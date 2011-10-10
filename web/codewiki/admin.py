from codewiki.models import Code, View, Scraper, UserCodeRole, ScraperRunEvent, CodePermission, Vault
from django.contrib.auth.models import User
from django.contrib import admin
from django.db import models
from django.db.models import Count
from django import forms
# from django.contrib.admin import SimpleListFilter

class UserCodeRoleInlines(admin.TabularInline):
    model = UserCodeRole
    extra = 1

def mark_featured(modeladmin, request, queryset):
    queryset.update(featured=True)
mark_featured.short_description = 'Mark selected items as featured'

def mark_unfeatured(modeladmin, request, queryset):
    queryset.update(featured=False)
mark_unfeatured.short_description = 'Mark selected items as unfeatured'

# This won't work until Django 1.4
#class HasVaultFilter(SimpleListFilter):
#    title = _('has vault')
#    parameter_name = 'has_vault'
#
#    def lookups(self, request, model_admin):
#        return (
#            ('yes', _('yes')),
#            ('no', _('no')),
#        )
#
#    def queryset(self, request, queryset):
#        if self.value() == 'yes':
#            return queryset.filter(vault=None)
#        if self.value() == 'no':
#            return queryset.exclude(vault=None)

class CodeAdmin(admin.ModelAdmin):
    inlines = (UserCodeRoleInlines,)    
    readonly_fields = ('wiki_type','guid')
    list_display = ('title', 'short_name', 'owner_name', 'status', 'privacy_status', 'vault_name')
    list_filter = ('status', 'privacy_status', 'featured', 'created_at')
    search_fields = ('title', 'short_name')

    def vault_name(self, obj):
        if obj.vault:
            return obj.vault.name
        return None

    def owner_name(self, obj):
        if obj.owner():
            return obj.owner().username
        return None

class ScraperAdmin(CodeAdmin):
    actions = [mark_featured, mark_unfeatured]

class ViewAdmin(CodeAdmin):
    actions = [mark_featured, mark_unfeatured]


# Override sort order of user objects by replacing form element, as per:
# http://stackoverflow.com/questions/923799/reorder-users-in-django-auth/1158484#1158484
class VaultAdminForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(queryset=User.objects.order_by('username'))
    class Meta:
        model = Vault

class VaultAdmin(admin.ModelAdmin):
    """
    Administration for a vault object, not sure yet whether we should hide
    the membership list so that we (scraperwiki) can't see it.
    """
    def queryset(self, request):
        return Vault.objects.annotate(member_count=Count('members'))
    def member_count(self, inst):
        return inst.member_count
    member_count.admin_order_field = 'member_count'

    list_display = ('name', 'user', 'plan', 'created_at', 'member_count')
    list_filter = ('plan', 'created_at')
    search_fields = ('name',)

    form = VaultAdminForm

class ScraperRunEventAdmin(admin.ModelAdmin):
    list_display = ('run_id', 'scraper', 'run_started', 'run_ended', 'pages_scraped', 'first_url_scraped')
    search_fields = ('first_url_scraped',)

admin.site.register(Scraper, ScraperAdmin)
admin.site.register(View, ViewAdmin)
admin.site.register(Vault, VaultAdmin)
admin.site.register(ScraperRunEvent, ScraperRunEventAdmin)
admin.site.register(CodePermission)




