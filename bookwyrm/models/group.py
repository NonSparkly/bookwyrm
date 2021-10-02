""" do book related things with other users """
from django.apps import apps
from django.db import models, IntegrityError, models, transaction
from django.db.models import Q
from bookwyrm.settings import DOMAIN
from .base_model import BookWyrmModel
from . import fields
from .relationship import UserBlocks
# from .user import User

class BookwyrmGroup(BookWyrmModel):
    """A group of users"""

    name = fields.CharField(max_length=100)
    user = fields.ForeignKey(
        "User", on_delete=models.PROTECT)
    description = fields.TextField(blank=True, null=True)
    privacy = fields.PrivacyField()

class BookwyrmGroupMember(models.Model):
    """Users who are members of a group"""
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    group = models.ForeignKey(
        "BookwyrmGroup", 
        on_delete=models.CASCADE,
        related_name="memberships"
    )
    user = models.ForeignKey(
        "User", 
        on_delete=models.CASCADE,
        related_name="memberships"
        )

    class Meta:
        constraints = [
          models.UniqueConstraint(
            fields=["group", "user"], name="unique_membership"
          )
        ]

    def save(self, *args, **kwargs):
        """don't let a user invite someone who blocked them"""
        # blocking in either direction is a no-go
        if UserBlocks.objects.filter(
            Q(
                user_subject=self.group.user,
                user_object=self.user,
            )
            | Q(
                user_subject=self.user,
                user_object=self.group.user,
            )
        ).exists():
            raise IntegrityError()
        # accepts and requests are handled by the BookwyrmGroupInvitation model
        super().save(*args, **kwargs)

    @classmethod
    def from_request(cls, join_request):
        """converts a join request into a member relationship"""

        # remove the invite
        join_request.delete()

        # make a group member
        return cls.objects.create(
            user=join_request.user,
            group=join_request.group,
        )


class GroupMemberInvitation(models.Model):
    """adding a user to a group requires manual confirmation"""
    created_date = models.DateTimeField(auto_now_add=True)
    group = models.ForeignKey(
        "BookwyrmGroup", 
        on_delete=models.CASCADE,
        related_name="user_invitations"
    )
    user = models.ForeignKey(
        "User", 
        on_delete=models.CASCADE,
        related_name="group_invitations"
        )

    class Meta:
        constraints = [
          models.UniqueConstraint(
            fields=["group", "user"], name="unique_invitation"
          )
        ]
    def save(self, *args, **kwargs):  # pylint: disable=arguments-differ
        """make sure the membership doesn't already exist"""
        # if there's an invitation for a membership that already exists, accept it
        # without changing the local database state
        if BookwyrmGroupMember.objects.filter(
            user=self.user,
            group=self.group
        ).exists():
            self.accept()
            return

        # blocking in either direction is a no-go
        if UserBlocks.objects.filter(
            Q(
                user_subject=self.group.user,
                user_object=self.user,
            )
            | Q(
                user_subject=self.user,
                user_object=self.group.user,
            )
        ).exists():
            raise IntegrityError()

        # make an invitation
        super().save(*args, **kwargs)

        # now send the invite
        model = apps.get_model("bookwyrm.Notification", require_ready=True)
        notification_type = "INVITE"
        model.objects.create(
            user=self.user,
            related_user=self.group.user,
            related_group=self.group,
            notification_type=notification_type,
        )

    def accept(self):
        """turn this request into the real deal"""

        with transaction.atomic():
            BookwyrmGroupMember.from_request(self)
            self.delete()

            # let the other members know about it
            model = apps.get_model("bookwyrm.Notification", require_ready=True)
            for member in self.group.members.all:
                if member != self.user:
                    model.objects.create(
                        user=member,
                        related_user=self.user,
                        related_group=self.group,
                        notification_type="ACCEPT",
                    )

    def reject(self):
        """generate a Reject for this membership request"""

        self.delete()

        # TODO: send notification