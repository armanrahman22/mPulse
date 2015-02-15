from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.core.files.storage import FileSystemStorage
from mpulse_site.util import getSessionFilePath, getLogFilePath
from django.conf import settings
from django.forms.models import modelform_factory
from django.forms import PasswordInput, ModelForm
from django.contrib import auth
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
import datetime
from django.utils import timezone
from django import forms

#Filepath var
fs = FileSystemStorage(location=settings.ABS_PATH_TO_FILES+'/uploads/')

#Kiosk class that maintains information about kiosks
class Kiosk(models.Model):
    name = models.CharField(max_length=200)
    owners = models.ManyToManyField(User)
    registration_key = models.CharField(max_length=8)
    is_registered = models.BooleanField(default=False)
    ip = models.GenericIPAddressField(null=True,blank=True)
    location = models.CharField(max_length=200,null=True,blank=True)
    gpsLocLat = models.FloatField(null=True,blank=True)
    gpsLocLong = models.FloatField(null=True,blank=True)
    
    secret_key = models.CharField(max_length=10,null=True,blank=True) #For making sure session data posted to the site is coming from a raspi
    
    STATUS_CHOICES = (
        ('O', 'Online'),
        ('E', 'Error'),
        ('F', 'Offline'),
    )
    status = models.CharField(max_length=1,choices=STATUS_CHOICES,null=True,blank=True)
    lastCheckIn = models.DateTimeField(null=True,blank=True)
    logFile = models.FileField(upload_to=getLogFilePath,storage=fs,null=True,blank=True)
    
    def checkForOffline(self):
        if self.status == 'O' and (not self.lastCheckIn or timezone.now() >= (self.lastCheckIn + datetime.timedelta(hours=3))):
            self.status = 'F'
    
    def __unicode__(self):
        return self.name+'@'+str(self.ip)
    
class KioskRegistrationForm(ModelForm):
    class Meta:
        model = Kiosk
        exclude = ["owners","registration_key","is_registered","ip","secret_key","status","lastCheckIn","logFile"]
        
    def clean_name(self):
        name = self.cleaned_data.get('name')
        existingName = self.instance.name
        if name and Kiosk.objects.filter(name=name).count() > 0 and name != existingName:
            raise forms.ValidationError(u'This kiosk name is already registered')
        return name
    
#Add a isKioskAdmin check function to the User class
def isKioskAdmin(self):
    return (bool(self.groups.filter(name='kioskAdmin')) or self.is_superuser or self.is_staff)

auth.models.User.add_to_class('isKioskAdmin', isKioskAdmin)

#UserProfile class that contains additional user information
class UserProfile(models.Model):
    user = models.OneToOneField(User)
    birthdate = models.DateField(null=True,blank=True)
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
    )
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES,null=True,blank=True)
    ETHNICITY_CHOICES = (
        ('A','African'),
        ('AAm','African-American or African-European'),
        ('SCA','South or Central American'),
        ('EA','East Asian'),
        ('ME','Middle-Eastern'),
        ('NA','Native American or Alaska Native'),
        ('PI','Pacific Islander'),
        ('SA','South Asian'),
        ('W','White American or European'),
        ('O','Other'),
    )
    ethnicity = models.CharField(max_length=3,choices=ETHNICITY_CHOICES,null=True,blank=True)
    ECONOMIC_CHOICES = (
        ('L','Low-Income (Below the Poverty Line for your state)'),
        ('M','Mid-Income'),
        ('H','High-Income (Living expenses account for less than 10% of your total income)')
    )
    economic = models.CharField(max_length=1, choices=ECONOMIC_CHOICES,null=True,blank=True)
    EDUCATION_CHOICES = (
        ('N','No schooling'),
        ('E', 'Nursery school through 8th grade'),
        ('S', 'Some High School'),
        ('H','High School Degree or Equivalent'),
        ('C','Some College'),
        ('V','Vocational / Trade / Technical Training'),
        ('A','Associate Degree'),
        ('B', "Bachelor's Degree"),
        ('M', "Master's Degree"),
        ('P', "Professional Degree"),
        ('D', "Doctorate Degree"),
    )
    education = models.CharField(max_length=1,choices=EDUCATION_CHOICES,null=True,blank=True)
    #Most recent, also stored on a session by session basis
    height = models.DecimalField(max_digits=5,decimal_places=2,null=True,blank=True)
    weight = models.DecimalField(max_digits=6,decimal_places=2,null=True,blank=True)
    
#Forms for users and user profiles
class UserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username","email","first_name","last_name"]
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).count() > 0:
            raise forms.ValidationError(u'This email address is already registered.')
        return email
    
class EditUserForm(UserChangeForm):
    class Meta:
        model = User
        fields = ["username","email","first_name","last_name"]
        exclude = ["password"]
        
    def __init__(self,*args,**kwargs):
        self.request = kwargs.pop('request',None)
        super(EditUserForm,self).__init__(*args,**kwargs)
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and email != self.request.user.email and User.objects.filter(email=email).count() > 0:
            raise forms.ValidationError(u'This email address is already registered.')
        return email
    
    def clean_password(self):
        return ""
    
class SetupUserForm(UserChangeForm):
    class Meta:
        model = User
        fields = ["first_name","last_name"]
        

UserProfileForm = modelform_factory(UserProfile, fields=("birthdate","gender","height","weight","ethnicity","economic","education"))

    

#Method to create a UserProfile automatically when a user is created
#def create_user_profile(sender, instance, created, **kwargs):  
#    if created:  
#       profile, created = UserProfile.objects.get_or_create(user=instance)  
#
#post_save.connect(create_user_profile, sender=User)

#Session class containing information from a particular session
class Session(models.Model):
        user = models.ForeignKey(User)
        
        datetime_taken = models.DateTimeField()
        datetime_saved = models.DateTimeField(auto_now_add=True)
        
        TYPE_CHOICES = (
            ('K','Kiosk'),
            ('S','Self'),
            ('H','Healthcare Professional')
        )
        type = models.CharField(max_length=1,choices=TYPE_CHOICES,default='K')
        kiosk = models.ForeignKey(Kiosk,null=True,blank=True) #If the type was kiosk, which kiosk it came from
        
        #Height and weight at the time of the session
        #Added to sessionData
        #height = models.DecimalField(max_digits=5,decimal_places=2,null=True,blank=True)
        #weight = models.DecimalField(max_digits=6,decimal_places=2,null=True,blank=True)
        
        #Data
        sessionData = models.TextField(null=True,blank=True)
        graphData = models.TextField(null=True,blank=True)
        uploads = models.FileField(upload_to=getSessionFilePath,storage=fs,null=True,blank=True) #Zip archive of any uploaded files
        
        def __unicode__(self):
            return self.user.username +' : ' + self.type + ' : ' + str(self.datetime_taken)
        
        #Method to get a sessionData variable by name (returns [name,val,unit] triplet)
        def getSessionDataVar(self,name):
            for var in eval(self.sessionData):
                if var[0] == name:
                    return var[1]
            return None
        
#ServerError class - used to store error reports from 500 errors
class ServerError(models.Model):
        time = models.DateTimeField(auto_now_add=True)
        html = models.TextField(null=True)
        #request = models.TextField(null=True)
        