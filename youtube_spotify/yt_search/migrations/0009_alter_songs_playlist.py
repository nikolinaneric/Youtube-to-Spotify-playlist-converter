# Generated by Django 4.1.7 on 2023-03-11 11:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('yt_search', '0008_alter_usertoken_uuid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='songs',
            name='playlist',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='yt_search.playlists'),
        ),
    ]
