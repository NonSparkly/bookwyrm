""" test for app action functionality """
from unittest.mock import patch

from django.template.response import TemplateResponse
from django.test import TestCase
from django.test.client import RequestFactory

from bookwyrm import models, views
from bookwyrm.tests.validate_html import validate_html


@patch("bookwyrm.models.activitypub_mixin.broadcast_task.delay")
class GroupViews(TestCase):
    """view group and edit details"""

    def setUp(self):
        """we need basic test data and mocks"""
        self.factory = RequestFactory()
        with patch("bookwyrm.suggested_users.rerank_suggestions_task.delay"), patch(
            "bookwyrm.activitystreams.populate_stream_task.delay"
        ):
            self.local_user = models.User.objects.create_user(
                "mouse@local.com",
                "mouse@mouse.mouse",
                "password",
                local=True,
                localname="mouse",
            )
        with patch("bookwyrm.models.user.set_remote_server.delay"):
            self.remote_user = models.User.objects.create_user(
                "rat",
                "rat@rat.com",
                "ratword",
                local=False,
                remote_id="https://example.com/users/rat",
                inbox="https://example.com/users/rat/inbox",
                outbox="https://example.com/users/rat/outbox",
            )

        with patch():
            self.testgroup = models.Group.objects.create(
              id=999,
              name="Test Group",
              user=self.local_user,
              privacy="public"
            )
            self.membership = models.GroupMember.objects.create(
                group=self.testgroup, user=self.local_user
            )

        models.SiteSettings.objects.create()

    def test_group_get(self, _):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Group.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        result = view(request)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_usergroups_get(self, _):
        """there are so many views, this just makes sure it LOADS"""
        view = views.UserGroups.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        result = view(request)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_findusers_get(self, _):
        """there are so many views, this just makes sure it LOADS"""
        view = views.FindUsers.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        result = view(request)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_group_post(self, _):
        """edit a "group" database entry"""
        view = views.Group.as_view()
        self.factory.post(
          group_id=999,
          name="Test Group",
          user=self.local_user,
          privacy="public",
          description="Test description",
        )

        self.assertEqual("Test description", self.testgroup.description)