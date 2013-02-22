from frontend.models import *
from codewiki.models import Vault, UserCodeRole
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

class MessageAdmin(admin.ModelAdmin):
    pass



class UserProfileStack(admin.StackedInline):
    model = UserProfile

    fk_name = 'user'
    max_num = 1
    extra = 0

class VaultInlines(admin.StackedInline):
    model = Vault
    extra = 0
 
class UserProfileInlines(admin.StackedInline):
    model = UserProfile
    extra = 0
    can_delete = False


def make_beta(modeladmin, request, queryset):
    for x in queryset.all():
        p = x.get_profile()
        p.beta_user = True
        p.save()
make_beta.short_description = 'Mark user as a beta user'

def remove_beta(modeladmin, request, queryset):
    for x in queryset.all():
        p = x.get_profile()
        p.beta_user = False
        p.save()
remove_beta.short_description = 'Mark user as NOT beta user'

class DataEnquiryAdmin(admin.ModelAdmin):
    list_display = ('date_of_enquiry', 'description', 'email', 'name', 'phone',)
    ordering = ('-date_of_enquiry',)

class FeaturesAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_description', 'public')
    
    def short_description(self, obj):
        if len(obj.description) > 50:
            return obj.description[:50] + '...'
        return obj.description
    
    class Meta:
        model = Feature

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'profile_name', 'email', 'scrapers', 'vaults', 'is_active', 'is_staff','is_beta_user','date_joined', 'last_login',)
    list_filter = ('is_active', 'is_staff', 'is_superuser',)
    ordering = ('-date_joined',)
    search_fields  = ('username','email',)
    actions = [make_beta, remove_beta]

    def is_beta_user(self, obj):
        if obj.get_profile().beta_user:
            return 'YES'
        else:
            return 'no'

    def scrapers(self, obj):
        return UserCodeRole.objects.filter(user=obj, role='owner').count()    

    def vaults(self, obj):
        return obj.vaults.count()
        
    def profile_name(self, obj):
        return obj.get_profile().name

    inlines = [UserProfileStack, VaultInlines]


admin.site.register(Feature, FeaturesAdmin)

admin.site.register(Message, MessageAdmin)
admin.site.register(DataEnquiry, DataEnquiryAdmin)

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

