from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag, Recipe
from recipe.serializers import TagSerializer

TAGS_URL = reverse('recipe:tag-list')


class PublicTagsApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            'test@example.com',
            'Test@123'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        Tag.objects.create(user=self.user, name='Vegan')
        Tag.objects.create(user=self.user, name='Dessert')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_limited_to_user(self):
        """Test that tag returns are for the authenticated user"""
        user2 = get_user_model().objects.create_user(
            'other@example.com',
            'Test@123'
        )
        Tag.objects.create(user=user2, name='Fruity')
        tag = Tag.objects.create(user=self.user, name='Comfort Food')

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)

    def test_filter_tags_already_assigned_to_recipes(self):
        tag1 = Tag.objects.create(user=self.user, name='Lunch')
        tag2 = Tag.objects.create(user=self.user, name='Dinner')

        recipe = Recipe.objects.create(
            user=self.user,
            title='Chicken Rice',
            time_minutes=20,
            price=10.00
        )
        recipe.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        serializer1 = TagSerializer(tag1)
        serializer2 = TagSerializer(tag2)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_assigned_return_unique(self):
        tag = Tag.objects.create(user=self.user, name='Lunch')
        Tag.objects.create(user=self.user, name='Breakfast')
        recipe1 = Recipe.objects.create(
            user=self.user,
            title='Chicken Rice',
            time_minutes=15,
            price=15.00
        )
        recipe2 = Recipe.objects.create(
            user=self.user,
            title='Fried Potato',
            time_minutes=15,
            price=5.00
        )
        recipe1.tags.add(tag)
        recipe1.refresh_from_db()

        recipe2.tags.add(tag)
        recipe2.refresh_from_db()

        res = self.client.get(TAGS_URL, {'assigned_only': 1})
        self.assertEqual(len(res.data), 1)
