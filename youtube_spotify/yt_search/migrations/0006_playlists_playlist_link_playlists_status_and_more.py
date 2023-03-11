# Generated by Django 4.1.7 on 2023-03-09 16:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('yt_search', '0005_usertoken'),
    ]

    operations = [
        migrations.AddField(
            model_name='playlists',
            name='playlist_link',
            field=models.CharField(default='', max_length=255),
        ),
        migrations.AddField(
            model_name='playlists',
            name='status',
            field=models.CharField(default='in progress', max_length=255),
        ),
        migrations.AddField(
            model_name='usertoken',
            name='user_id',
            field=models.CharField(default='', max_length=255),
        ),
    ]