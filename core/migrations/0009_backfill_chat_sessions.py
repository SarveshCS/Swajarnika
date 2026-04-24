from django.db import migrations


def backfill_sessions(apps, schema_editor):
    ChatSession = apps.get_model('core', 'ChatSession')
    AIChatMessage = apps.get_model('core', 'AIChatMessage')
    Patient = apps.get_model('core', 'Patient')

    for patient in Patient.objects.all():
        orphan = AIChatMessage.objects.filter(patient=patient, session__isnull=True).order_by('created_at')
        if not orphan.exists():
            continue
        first = orphan.first()
        title = (first.message[:60] + ('…' if len(first.message) > 60 else '')) if not first.is_ai else 'Previous conversation'
        session = ChatSession.objects.create(patient=patient, title=title)
        orphan.update(session=session)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0008_chatsession_aichatmessage_session'),
    ]

    operations = [
        migrations.RunPython(backfill_sessions, noop),
    ]
