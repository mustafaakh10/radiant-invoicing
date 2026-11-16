from django.db import models


class Record(models.Model):
    """One document of the app's data, addressed like the app addresses it:
    "products/p_trail3w", "docs/dq_…", "settings/main", "counters/QT-2026"."""
    path = models.CharField(max_length=300, primary_key=True)
    collection = models.CharField(max_length=100, db_index=True)
    data = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *a, **kw):
        self.collection = self.path.rsplit("/", 1)[0]
        super().save(*a, **kw)

    def __str__(self):
        return self.path


class Revision(models.Model):
    """A single counter bumped on every change, so open tabs/phones know when to refresh."""
    rev = models.BigIntegerField(default=0)

    @classmethod
    def bump(cls):
        obj, _ = cls.objects.select_for_update().get_or_create(pk=1)
        obj.rev += 1
        obj.save(update_fields=["rev"])
        return obj.rev

    @classmethod
    def current(cls):
        obj = cls.objects.filter(pk=1).first()
        return obj.rev if obj else 0


class Upload(models.Model):
    file = models.FileField(upload_to="uploads/%Y/%m/")
    content_type = models.CharField(max_length=80, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    @property
    def url(self):
        return self.file.url


class AIConfig(models.Model):
    """Your AI provider settings. The key never leaves the server."""
    provider = models.CharField(max_length=30, default="none")
    base = models.CharField(max_length=300, blank=True)
    model = models.CharField(max_length=120, blank=True)
    key = models.TextField(blank=True)
    monthly_token_limit = models.PositiveIntegerField(default=0, help_text="0 = no limit")

    @classmethod
    def get(cls):
        return cls.objects.get_or_create(pk=1)[0]


class AICall(models.Model):
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    provider = models.CharField(max_length=30)
    model = models.CharField(max_length=120)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cached = models.BooleanField(default=False)
    ok = models.BooleanField(default=True)
    error = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created"]


class AICache(models.Model):
    """Same prompt to the same model again: answer from here, zero tokens."""
    key = models.CharField(max_length=64, primary_key=True)
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
