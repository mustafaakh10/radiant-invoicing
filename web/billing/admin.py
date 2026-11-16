from django.contrib import admin

from .models import AICall, AIConfig, Record, Upload


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ("path", "collection", "updated_at")
    list_filter = ("collection",)
    search_fields = ("path",)


@admin.register(AICall)
class AICallAdmin(admin.ModelAdmin):
    list_display = ("created", "provider", "model", "input_tokens", "output_tokens", "cached", "ok")
    list_filter = ("cached", "ok", "provider")


@admin.register(AIConfig)
class AIConfigAdmin(admin.ModelAdmin):
    list_display = ("provider", "model", "monthly_token_limit")
    exclude = ("key",)  # set the key from the app's Settings, it is never shown back


admin.site.register(Upload)
