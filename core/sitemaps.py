from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from core.models import ResearchPublication
from software_store.models import SoftwareProduct


class StaticViewSitemap(Sitemap):

    priority = 0.8

    changefreq = 'weekly'

    def items(self):

        return [

            'home',

            'services',

            'portfolio',

            'research',

            'contact',

            'about',

        ]

    def location(self, item):

        return reverse(item)


class SoftwareProductSitemap(Sitemap):

    changefreq = 'weekly'

    priority = 0.8

    def items(self):

        return SoftwareProduct.objects.filter(
            is_active=True
        )

    def lastmod(self, item):

        return item.updated_at

    def location(self, item):

        return reverse(
            'software_product_detail',
            args=[
                item.slug,
            ]
        )


class ResearchPublicationSitemap(Sitemap):

    changefreq = 'monthly'

    priority = 0.7

    def items(self):

        return ResearchPublication.objects.filter(
            is_published=True
        )

    def lastmod(self, item):

        return item.updated_at

    def location(self, item):

        return reverse(
            'research_detail',
            args=[
                item.slug,
            ]
        )
