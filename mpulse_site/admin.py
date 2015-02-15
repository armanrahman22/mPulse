from django.contrib import admin
from mpulse_site.models import Kiosk,UserProfile,Session,ServerError
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

#Inline for profiles to be displayed in 
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'
    
class UserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    
class KioskAdmin(admin.ModelAdmin):
    #exclude = ('secret_key',)
    pass

admin.site.unregister(User)
admin.site.register(User,UserAdmin)

admin.site.register(Kiosk,KioskAdmin)
#admin.site.register(Session)