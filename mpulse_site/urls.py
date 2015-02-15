from django.conf.urls import patterns, url

from mpulse_site import views
from django.conf.urls import patterns, url, include
from django.contrib.auth.views import password_reset,password_reset_done, password_reset_confirm, password_reset_complete

urlpatterns = patterns('mpulse_site.views',
    #Home page, help
    url(r'^$', 'index', name='index'),
    url(r'^help/$','help',name="help"),
    
    #Login / logout
    url(r'^login/go/$','login_action',name="login_action"),
    url(r'^login/$','login_prompt',name="login_prompt"),
    url(r'^logout/$','logout_action',name="logout"),
    
    #Accounts
    url(r'^accounts/create/$','create_account',name="create_account"),
    url(r'^accounts/edit/$','edit_account',name="edit_account"),
    url(r'^accounts/setup/$','setup_account',name="setup_account"), #Used for setting up an account that was created from a kiosk
    #url(r'^accounts/password_reset/$', password_reset, name="password_reset"),
    url(r'^accounts/password_reset/$', password_reset, {'template_name': 'password_reset.html'},name="password_reset"),
    url(r'^accounts/password_reset_done/$', password_reset_done,{'template_name':'password_reset_done.html'},name="password_reset_done"),
    url(r'^accounts/password_reset_confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/$', password_reset_confirm,{'template_name':'password_reset_confirm.html'},name="password_reset_confirm"),
    url(r'^accounts/password_reset_complete/$', password_reset_complete,{'template_name':'password_reset_complete.html'},name="password_reset_complete"),
    
    #Kiosk location map
    url(r'^kiosks/$','kiosks', name='kiosks'),
    url(r'^kiosks/xml/$','kiosksXML', name='kiosksXML'),
    
    #Profiles and Sessions
    url(r'^profile/$','profile',name="profile"),
    url(r'^session/(?P<session_id>[0-9]+)/$','session',name="session"),
    url(r'^session/(?P<session_id>[0-9]+)/delete/$','deleteSession',name="deleteSession"),
    url(r'^session/export/(?P<session_id>[0-9]+)/$','exportSession',name="exportSession"),
    url(r'^session/email/(?P<session_id>[0-9]+)/$','emailSession',name="emailSession"),
    
    #Post session data from kiosk
    url(r'^session/saveData/$','saveSessionData',name="saveSessionData"),
    url(r'^session/emailData/$','emailSessionData',name="emailSessionData"),
    
    #Charts
    url(r'^profile/chartSessionVar/$','chartSessionVar',name="chartSessionVar"),
 #   url(r'^profile/chartWeight/$','chartWeight',name="chartWeight"),
 #   url(r'^profile/chartHeight/$','chartHeight',name="chartHeight"),
 #   url(r'^profile/chartBMI/$','chartBMI',name="chartBMI"),
    
    #Admin
    url(r'^manage/$','manage', name='manage'),
    
    #Register kiosk
    url(r'^kiosks/register/$','registerKiosk',name='registerKiosk'),
    url(r'^kiosks/hardwareRegister/$','kiosk_registration',name='kioskRegistration'),
    
    #Kiosk management, updates and log
    url(r'^updateCode/$','updateCode',name="updateCode"),
    #url(r'^admin/forceUpdateCode/(?P<kiosk_id>[0-9]+)/$','forceUpdateCode',name="forceUpdateCode"),
    url(r'^admin/viewKioskLog/(?P<kiosk_id>[0-9]+)/$','viewKioskLog',name="viewKioskLog"),
    url(r'^admin/editKiosk/(?P<kiosk_id>[0-9]+)/$','editKiosk',name="editKiosk"),
    url(r'^admin/addKioskOwner/(?P<kiosk_id>[0-9]+)/$','addKioskOwner',name="addKioskOwner"),
    url(r'^admin/removeKioskOwner/(?P<kiosk_id>[0-9]+)/(?P<owner_id>[0-9]+)/$','removeKioskOwner',name="removeKioskOwner"),
    
    #Docs
    url(r'^docs/downloadPrivateFile/(?P<filename>[a-zA-Z0-9\.]+)$','downloadPrivateFile',name='downloadPrivateFile'),
    
    #Error handling / viewing
    url(r'^admin/errorsList/$','errorsList',name='errorsList'),
    url(r'^admin/getErrorPage/$','getErrorPage',name="getErrorPage"),
    url(r'^admin/deleteError/(?P<error_id>[0-9]+)/$','deleteError',name="deleteError"),
    
    #test
    url(r'^test/$','test',name="test"),
)
