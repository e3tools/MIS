# Generated by Django 4.1.1 on 2022-11-25 20:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subprojects', '0012_subproject_allocation_alter_subproject_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subproject',
            name='created_date',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name='subproject',
            name='updated_date',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]
