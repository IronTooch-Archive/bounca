# Generated by Django 3.2.7 on 2021-10-17 07:36

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('x509_pki', '0009_auto_20211017_0921'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='keystore',
            name='crl',
        ),
        migrations.CreateModel(
            name='CrlStore',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('crl', models.TextField(blank=True, null=True, verbose_name='Serialized CRL certificate')),
                ('certificate', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='x509_pki.certificate')),
            ],
        ),
    ]
