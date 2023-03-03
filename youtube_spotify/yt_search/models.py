from django.db import models

# Create your models here.
# class CacheEntry(models.Model):
#     key = models.CharField(max_length=255, unique=True)
#     value = models.TextField()

#     class Meta:
#         db_table = 'my_cache_table'

class Songs(models.Model):
    title = models.CharField(max_length=255)

    class Meta:
        db_table = 'songs'
