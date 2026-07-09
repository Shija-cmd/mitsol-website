from django.test import TestCase
from django.urls import reverse

from .models import ResearchPublication


class ResearchPageTests(TestCase):

    def test_research_page_shows_published_publications(self):

        publication = ResearchPublication.objects.create(
            title='Machine Learning Model for Early Detection of STIs',
            category=ResearchPublication.Category.PUBLICATION,
            abstract='A predictive model for healthcare decision support.',
            authors='Juma M. Shija',
            research_area='Machine Learning, Health Informatics',
            is_published=True
        )

        response = self.client.get(
            reverse('research')
        )

        self.assertContains(
            response,
            'Machine Learning Model for Early Detection of STIs'
        )
        self.assertContains(
            response,
            'Machine Learning, Health Informatics'
        )
        self.assertContains(
            response,
            reverse(
                'research_detail',
                args=[
                    publication.slug,
                ]
            )
        )

    def test_research_page_hides_unpublished_publications(self):

        ResearchPublication.objects.create(
            title='Hidden Draft Research',
            abstract='This should not appear publicly.',
            is_published=False
        )

        response = self.client.get(
            reverse('research')
        )

        self.assertNotContains(
            response,
            'Hidden Draft Research'
        )

    def test_research_detail_shows_structured_sections(self):

        publication = ResearchPublication.objects.create(
            title='AI-Driven Predictive Analytics',
            category=ResearchPublication.Category.RESEARCH_PROJECT,
            status=ResearchPublication.Status.COMPLETED,
            abstract='Predictive analytics research.',
            objectives='Improve decision support.',
            methodology='Machine learning experiments.',
            results='Improved prediction accuracy.',
            conclusion='AI can support practical decisions.',
            future_work='Expand datasets.',
            authors='MITSOL Research Team',
            keywords='AI, Machine Learning',
            technologies_used='Python, Django',
            is_published=True
        )

        response = self.client.get(
            reverse(
                'research_detail',
                args=[
                    publication.slug,
                ]
            )
        )

        self.assertContains(
            response,
            'Objectives'
        )
        self.assertContains(
            response,
            'Machine learning experiments.'
        )
        self.assertContains(
            response,
            'Python'
        )
