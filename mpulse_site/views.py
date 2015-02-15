from django.http import HttpResponse,HttpResponseRedirect, HttpResponseServerError
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied

from django.shortcuts import render_to_response, get_object_or_404, get_list_or_404
from django.template.loader import render_to_string

from django.template import RequestContext
from django.shortcuts import render

from django.contrib.auth import authenticate, login, logout

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.debug import sensitive_variables, sensitive_post_parameters

from mpulse_site.models import Kiosk, Session, UserProfile, UserForm,UserProfileForm, EditUserForm, KioskRegistrationForm, ServerError
from django.contrib.auth.models import User

from datetime import date,datetime
from time import strptime,mktime
from django.utils import timezone
from django.utils.dateformat import DateFormat

from django.core.mail import EmailMessage, send_mail

from util import sessionPDF, get_file_contents
from django.core.files.base import ContentFile

from django.conf import settings

from django.views.debug import ExceptionReporter

import subprocess, re,sys
import random
import paramiko #ssh


####################### User Permissions ############################
#Returns true if a user is in the kioskAdmin group or is a superuser
def isKioskAdmin(user):
    if user:
        return (bool(user.groups.filter(name='kioskAdmin')) or user.is_superuser or user.is_staff)
    return False
    
######################### INDEX / HELP ####################################

def index(request):
    return render_to_response('index.html',context_instance=RequestContext(request));
    
def help(request):
    message = None
    if request.method == "GET" and 'message' in request.GET:
        message = request.GET['message']
    return render_to_response('help.html',{'message':message},context_instance=RequestContext(request));
    
######################## LOGIN / LOGOUT #################################

#Login page
def login_prompt(request):
    return render_to_response('login.html',context_instance=RequestContext(request))

#Login function - redirects to dashboard
@sensitive_variables('password')
@sensitive_post_parameters('password')
def login_action(request):
    if request.method == "POST":
        try:
            userByEmail = User.objects.get(email=request.POST['email'])
        except User.DoesNotExist:
            return render_to_response('login.html',{'error': 'User with that email does not exist'}, context_instance=RequestContext(request))
        
        try:
            username = userByEmail.username
            password = request.POST['password']
            user = authenticate(username=username,password=password)
            
        except (KeyError, User.DoesNotExist): #If username/password blank
            #Render the login_prompt page with an error
            return render_to_response('login.html',{'error': 'Email or password was blank'}, context_instance=RequestContext(request))
        
        #If user is authenticated
        if user is not None:
            if user.is_active:
                login(request,user)
                return HttpResponseRedirect(reverse('mpulse_site.views.profile')) #Redirect to dashboard
            else:
                #Render the login_prompt page with an error
                return render_to_response('login.html',{'error': 'User has been disabled'}, context_instance=RequestContext(request))
            
        else:
            #Render the login_prompt page with an error
            return render_to_response('login.html',{'error': 'Invalid username or password'}, context_instance=RequestContext(request))
        
    return HttpResponseRedirect(reverse('mpulse_site.views.login_prompt'))

#Logout function - redirects to index
def logout_action(request):
    logout(request)
    return HttpResponseRedirect(reverse('mpulse_site.views.index')) #redirect to index

    
################################ Users ############################

#Create a new account
@sensitive_variables('userForm','userProfileForm')
@sensitive_post_parameters()
def create_account(request):
    #generate temporary username
    tmp_username = datetime.now().strftime("%B.%d.%Y.%I.%M.%p")
        
    if request.method == 'POST': # If form already submitted
        #bound forms
        userForm = UserForm(data = request.POST) 
        userProfileForm = UserProfileForm(data = request.POST)
        if userForm.is_valid() and userProfileForm.is_valid(): # All validation rules pass
            user = userForm.save()
            user.username = 'user'+str(user.pk)
            user.save()
            profile = userProfileForm.save(commit=False)
            profile.user = user
            profile.save()
            
            message = "Account Created Succesfully"
            return HttpResponseRedirect(("%s?message=" % reverse('mpulse_site.views.help'))+message) # Redirect after creation to help page
    else: #unbound forms
        userForm = UserForm()
        userProfileForm = UserProfileForm()
        
    return render_to_response('createAccount.html',{'userForm':userForm,'userProfileForm':userProfileForm,'tmp_username':tmp_username},context_instance=RequestContext(request))

#Shows a form to edit the user's account
@sensitive_variables('userForm','userProfileForm')
@sensitive_post_parameters()
@login_required
def edit_account(request):
    if request.method == 'POST': # If form already submitted
        #bound forms
        userForm = EditUserForm(data = request.POST,instance = request.user,request=request) 
        userProfileForm = UserProfileForm(data = request.POST,instance=request.user.get_profile())
        if userForm.is_valid() and userProfileForm.is_valid(): # All validation rules pass
            user = userForm.save()
            profile = userProfileForm.save()
            
            return HttpResponseRedirect(reverse('mpulse_site.views.profile')) # Redirect after creation to help page
    else: #unbound forms
        userForm = EditUserForm(instance=request.user)
        userProfileForm = UserProfileForm(instance=request.user.get_profile())
        
    return render_to_response('editAccount.html',{'userForm':userForm,'userProfileForm':userProfileForm},context_instance=RequestContext(request))

#Sets up a new user account
def setup_account(request):
    pass

#Shows a user profile
@sensitive_variables('user','sessions')
@login_required
def profile(request):
    user = get_object_or_404(User,username=request.user.username) #Get user by the given username or raise 404 if doesn't exist
    sessions = user.session_set.all().order_by('-datetime_taken')
    #Get age
    today = date.today()
    born = user.get_profile().birthdate
    if born:
        try: 
            birthday = born.replace(year=today.year)
        except ValueError: # birth date is February 29 and current year is not leap year
            birthday = born.replace(year=today.year, day=born.day-1)
    
        age =  today.year - born.year - (birthday > today)
    else:
        age = 'None'
    bmi = None
    bmiResult = ''
    if request.user.get_profile().weight and request.user.get_profile().height:
        height = request.user.get_profile().height * 12
        h = height**2
        bmi = request.user.get_profile().weight / h * 703
        
        #if bmi <= 18:
        #    bmiResult = 'underweight'
        #elif bmi <= 18.5:
        #    bmiResult = 'thin'
        #elif bmi <= 24.9:
        #    bmiResult = 'healthy'
        #elif bmi <= 29.9:
        #    bmiResult = 'overweight'
        #else:
        #    bmiResult = 'obese'
            
        bmi = format(bmi,'.2f')
        
    return render_to_response('profile.html',{'profile_user':user,'sessions':sessions,'userAge':age,'userBMI':bmi},context_instance=RequestContext(request))

############################### Sessions #####################################
@sensitive_variables('session')
@login_required
def session(request,session_id):
    session = get_object_or_404(Session,pk=session_id) #Get session by id number or raise 404 if doesn't exist
    if session.user == request.user: #if session belongs to the current user
        graphData = eval(session.graphData)
#        if graphData['ecg'][0] != None:
#            firstVal = graphData['ecg'][0][0]
#        else:
#            firstVal = 0
        #ecgData = [[(x[0]-firstVal)/10.0**6,x[1]] for x in graphData['ecg'] if x != None]
        if 'ecg' in graphData:
            ecgData = graphData['ecg']
        else:
            ecgData = None
        return render_to_response('session.html',{'session':session,'sessionData':eval(session.sessionData),'ecgData':ecgData},context_instance=RequestContext(request))
    else:
        raise PermissionDenied
        #return HttpResponseRedirect(reverse('mpulse_site.views.login_prompt'),context_instance=RequestContext(request))
    
@sensitive_variables('session')
@login_required
def deleteSession(request,session_id):
    session = get_object_or_404(Session,pk=session_id) #Get session by id number or raise 404 if doesn't exist
    if session.user == request.user: #if session belongs to the current user
        session.delete()
        return HttpResponseRedirect(reverse('mpulse_site.views.profile'))
    else:
        raise PermissionDenied
        #return HttpResponseRedirect(reverse('mpulse_site.views.login_prompt'),context_instance=RequestContext(request))  

@sensitive_variables('session')
@login_required
def emailSession(request,session_id):
    session = get_object_or_404(Session,pk=session_id) #Get session by id number or raise 404 if doesn't exist
    if session.user == request.user: #if session belongs to the current user
        graphData = eval(session.graphData)
        #ecgData = [[x[0]/10.0**6,x[1]] for x in graphData['ecg'] if x != None]
        if 'ecg' in graphData:
            ecgData = graphData['ecg']
        else:
            ecgData = None
        subject = 'M-Pulse Kiosk Session Results'
        message = 'Attached are your M-Pulse Kiosk Session Results from '+timezone.localtime(session.datetime_taken).strftime("%B %d %Y at %I:%M%p")+'. This email was sent on '+datetime.now().strftime("%B %d %Y at %I:%M%p")+'.'
        sender = settings.DEFAULT_FROM_EMAIL
        recipients = [session.user.email]
        email = EmailMessage(subject,message,sender,recipients,headers={'Reply-To':sender})
        buffer = sessionPDF(session.user.get_full_name(),timezone.localtime(session.datetime_taken),session.kiosk.location,eval(session.sessionData),ecgData)
        fileContents = buffer.getvalue()
        buffer.close()
        email.attach('SessionResults.pdf',fileContents,'application/pdf')
        email.send(fail_silently=False)
    
        return render_to_response('session.html',{'session':session,'sessionData':eval(session.sessionData),'ecgData':ecgData,'success_message':'Email sent to: '+session.user.email},context_instance=RequestContext(request))

    else:
        raise PermissionDenied
        #return HttpResponseRedirect(reverse('mpulse_site.views.login_prompt'),context_instance=RequestContext(request))
 
@sensitive_variables('session')   
@login_required
def exportSession(request,session_id):
    session = get_object_or_404(Session,pk=session_id) #Get session by id number or raise 404 if doesn't exist
    if session.user == request.user: #if session belongs to the current user
        graphData = eval(session.graphData)
        if 'ecg' in graphData:
            ecgData = graphData['ecg']
        else:
            ecgData = None
        buffer = sessionPDF(session.user.get_full_name(),timezone.localtime(session.datetime_taken),session.kiosk.location,eval(session.sessionData),ecgData)
        fileContents = buffer.getvalue()
        buffer.close()
    
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="SessionResults.pdf"'
        response.write(fileContents)
        return response
    else:
        raise PermissionDenied
        #return HttpResponseRedirect(reverse('mpulse_site.views.login_prompt'),context_instance=RequestContext(request))
  
#Saves session data to this site - called from a kiosk
@sensitive_variables('user','username','newUserProfile')
@sensitive_post_parameters('userEmail')
@csrf_exempt
def saveSessionData(request):
    if request.method == "POST":
            if 'kioskName' in request.POST and 'userEmail' in request.POST and 'datetimeTaken' in request.POST and 'sessionData' in request.POST and 'graphData' in request.POST and 'secret_key' in request.POST:
                try: #Get kiosk if it exists
                    kiosk = Kiosk.objects.get(name=request.POST['kioskName'])
                except Kiosk.DoesNotExist:
                    return HttpResponse('failure: kiosk does not exist on the website. Make sure kiosk is registered.')
                
                #Check to make sure the secret key matches the one sent from the kiosk on registration
                if kiosk.secret_key.strip() != request.POST['secret_key'].strip():
                    return HttpResponse('verification failure')
                
                try: #Get user if it exists
                    user = User.objects.get(email=request.POST['userEmail'])
                except User.DoesNotExist: #If user does not exist, create a new one. User can set password through the password reset interface
                    username = request.POST['userEmail'][:30]
                    user = User(username=username, email=request.POST['userEmail'])
                    user.save()
                    user.username='user'+str(user.pk) #set username to pk
                    user.save()
                    #Create userprofile and link to new user
                    newUserProfile = UserProfile(user=user)
                    newUserProfile.save()
                    
                    #Send an email to the user saying session results have been saved for them and request they create a password
                    send_mail('M-PULSE Kiosk Session Results Waiting', 'This message is to inform you that an account has been created for you at '+settings.DOMAIN+settings.SITE_ROOT+'/ and that you have session results saved there. Please go to '+settings.DOMAIN+reverse('password_reset')+' to set a password for your account.', settings.DEFAULT_FROM_EMAIL,  [request.POST['userEmail']], fail_silently=True)
                    
                timestamp = datetime.strptime(request.POST['datetimeTaken'],'%Y-%m-%d %H:%M:%S.%f')
                #Save data to new session
                newSession = Session(user=user,datetime_taken=timestamp,type='K',kiosk=kiosk,sessionData = request.POST['sessionData'],graphData = request.POST['graphData'])
                newSession.save()
                #Save the most current weight if available
                weightVar = newSession.getSessionDataVar('Weight')
                if weightVar:
                    userProfile = user.get_profile()
                    userProfile.weight = float(weightVar)
                    userProfile.save()
                
                return HttpResponse('success')
    return HttpResponse('no or imcomplete data')           
            
#Sends an email with session data - called from a kiosk
@sensitive_variables('user','username','newUserProfile')
@sensitive_post_parameters('userEmail')
@csrf_exempt
def emailSessionData(request):
    if request.method == "POST":
            if 'kioskName' in request.POST and 'userEmail' in request.POST and 'datetimeTaken' in request.POST and 'sessionData' in request.POST and 'graphData' in request.POST and 'secret_key' in request.POST:
                try: #Get kiosk if it exists
                    kiosk = Kiosk.objects.get(name=request.POST['kioskName'])
                except Kiosk.DoesNotExist:
                    return HttpResponse('failure: kiosk does not exist on the website. Make sure kiosk is registered.')
                
                #Check to make sure the secret key matches the one sent from the kiosk on registration
                if kiosk.secret_key.strip() != request.POST['secret_key'].strip():
                    return HttpResponse('verification failure')
                
                #create and email a pdf of the data to the user
                graphData = eval(request.POST['graphData'])
                if 'ecg' in graphData:
                    ecgData = graphData['ecg']
                else:
                    ecgData = None
                subject = 'M-Pulse Kiosk Session Results'
                timestamp = datetime.strptime(request.POST['datetimeTaken'],'%Y-%m-%d %H:%M:%S.%f')
                message = 'Attached are your M-Pulse Kiosk Session Results from '+timestamp.strftime("%B %d %Y at %I:%M%p")+'. This email was sent on '+datetime.now().strftime("%B %d %Y at %I:%M%p")+'.'
                sender = settings.DEFAULT_FROM_EMAIL
                recipients = [request.POST['userEmail']]
                email = EmailMessage(subject,message,sender,recipients,headers={'Reply-To':sender})
                buffer = sessionPDF(request.POST['userEmail'],timestamp,kiosk.location,eval(request.POST['sessionData']),ecgData)
                fileContents = buffer.getvalue()
                buffer.close()
                email.attach('SessionResults.pdf',fileContents,'application/pdf')
                email.send(fail_silently=False)
                return HttpResponse('success')
    return HttpResponse('no or incomplete data')   

############################### Charts #######################################
#Returns a rendered line chart of a session variable such as temperature. Used on the session pages
@login_required
def chartSessionVar(request):
    if request.method == 'GET' and 'varName' in request.GET:
        varName = request.GET["varName"]
        varUnits = ''
        data = []
        for session in request.user.session_set.exclude(sessionData__isnull=True).order_by('datetime_taken'):
            varVal = None
            for item in eval(session.sessionData):
                if item[0] == varName: 
                    varVal = item[1]
                    varUnits = item[2].strip()
            if varVal: #'2008-09-30 4:00PM'
                data.append([timezone.localtime(session.datetime_taken).strftime('%Y-%m-%d %I:%M%p'),float(varVal)])
    else:
        return HttpResponse('No session variable selected')
    if len(data) < 2:
        return HttpResponse('Not enough data to plot :(')
    return render_to_response('lineChart.html',{'title':varName,'data':data, 'yLabel':varUnits,'xLabel':'Date'},context_instance=RequestContext(request))

    
################################ KIOSKS / MANAGE######################################
#Displays a map of kiosk locations
def kiosks(request):              
    kiosks = Kiosk.objects.all()
    for kiosk in kiosks:
        kiosk.checkForOffline()
    lats,lngs = [kiosk.gpsLocLat for kiosk in kiosks if kiosk.gpsLocLat],[kiosk.gpsLocLong for kiosk in kiosks if kiosk.gpsLocLong]
    if len(lats) > 0 and len(lngs) > 0:    
        center = (sum(lats)/len(lats),sum(lngs)/len(lngs))
    else:
        center = (0,0)
    return render_to_response('kiosks.html',{'kiosks':kiosks,'center':center},context_instance=RequestContext(request))

#Returns an XML list of kiosks
def kiosksXML(request):
    kiosks = Kiosk.objects.exclude(gpsLocLat__isnull=True).exclude(gpsLocLong__isnull=True)
    for kiosk in kiosks:
        kiosk.checkForOffline()
    return render_to_response('kiosk_list_XML.xml',{'kiosks':kiosks})

#Page to register a kiosk if the user is already approved
@login_required
@user_passes_test(isKioskAdmin)
def registerKiosk(request):
    if request.method == 'POST': # If form already submitted
        #bound forms
        registrationForm = KioskRegistrationForm(data = request.POST) 
        if registrationForm.is_valid(): # All validation rules pass
            kiosk = registrationForm.save(commit=False)
            #Generate random registration key
            registration_key = ''.join(random.choice('0123456789ABCDEF') for i in range(8))
            kiosk.registration_key = registration_key
            message = "Your kiosk has been registered and its registration key is: "+registration_key+" (write this down, you'll need it to get your kiosk connected to this site)"
            kiosk.save()
            kiosk.owners.add(request.user)
            kiosk.save()
            
            return HttpResponseRedirect(("%s?message=" % reverse('mpulse_site.views.help'))+message) # Redirect after creation to help page
    else: #unbound forms
        registrationForm = KioskRegistrationForm()
        
    return render_to_response('registerKiosk.html',{'registrationForm':registrationForm},context_instance=RequestContext(request))

#Page that kiosks post to in order to set their first secret_key
@csrf_exempt
def kiosk_registration(request):
    if request.method == "POST":
        if 'kiosk_name' in request.POST and 'secret_key' in request.POST and 'registration_key' in request.POST:
            try:
                k = Kiosk.objects.get(name=request.POST['kiosk_name'])
                if k.is_registered: #check if kiosk already registered
                    return HttpResponse('Kiosk has already been succesfully registered.')
                #Check registration key
                if k.registration_key != request.POST['registration_key']:
                    return HttpResponse('Registration key incorrect')
                #If all is good, register the kiosk
                k.secret_key = request.POST['secret_key'].strip()
                k.is_registered = True
                k.save()
                return HttpResponse('Kiosk successfully registered')
            except Kiosk.DoesNotExist:
                return HttpResponse('Kiosk does not exist. Make sure to register your kiosk on the website.')
                

#Page to manage kiosks -> shows a user's owned kiosks and their status
# Kiosks post their IP address and log file to this page
@csrf_exempt
def manage(request):
        if request.method == "POST":
            #return HttpResponse(request.POST)
            if 'kiosk_name' in request.POST and 'ip' in request.POST and 'old_secret_key' in request.POST and 'new_secret_key' in request.POST: #and 'location' in request.POST:
                #update IP and check-in time
                try:
                    k = Kiosk.objects.get(name=request.POST['kiosk_name'])
                    
                    if k.secret_key != request.POST['old_secret_key']: #Check for correct secret key
                        return HttpResponse('Verification failure.')
                        
                    k.ip = request.POST['ip'].strip()
                    k.secret_key = request.POST['new_secret_key'].strip()
                    #k.location = request.POST['location']
                except Kiosk.DoesNotExist: #Make a new kiosk if this is the first time one tries to connect
                    #k = Kiosk(name=request.POST['kiosk_name'],ip=request.POST['ip'].strip(),secret_key=request.POST['new_secret_key'].strip())#,location=request.POST['location'])
                    return HttpResponse('Kiosk does not exist. Make sure to register your kiosk on the website.')
                    
                k.status = 'O'
                k.lastCheckIn = timezone.now()
                k.save()
                
                #save log file
                if 'logfile' in request.FILES:
                    #if k.logFile:
                    #    k.logFile.delete()

                    if k.logFile:
                        curContents = k.logFile.read()
                        newContents = curContents + request.FILES['logfile'].read()
                        k.logFile.delete()
                        k.logFile.save('log.txt',ContentFile(newContents),save=True)
                    else:
                        k.logFile = request.FILES['logfile']
                    k.save()
                else:
                    return HttpResponse('no log file uploaded')
                return HttpResponse('success')
            return HttpResponse('missing post data')   
        elif request.user.is_authenticated() and request.user.isKioskAdmin:
            if request.user.is_superuser:
                kiosks = Kiosk.objects.all()
            else:
                kiosks = request.user.kiosk_set.all()
            for kiosk in kiosks:
                kiosk.checkForOffline()
            return render_to_response('manage.html',{'kiosks':kiosks},context_instance=RequestContext(request))
        else:
            raise PermissionDenied
            #return HttpResponseRedirect(reverse('mpulse_site.views.login_prompt'))
        
        
##################################### Update Kiosk Code ############################################
#Provides a zip file of the kiosk code hosted on this server to requesting kiosks
@csrf_exempt
def updateCode(request):
    if request.method == "POST":
            if 'kiosk_name' in request.POST and 'secret_key' in request.POST: #and 'location' in request.POST:
                try:
                    k = Kiosk.objects.get(name=request.POST['kiosk_name'])
                    if k.secret_key != request.POST['secret_key']: #Check for correct secret key
                        return HttpResponse('kiosk verification failure')
                    #Return a zip file of the code
                    f = open('kioskCode.zip')
                    response = HttpResponse(f.read(), mimetype = "application/x-zip-compressed")
                    response['Content-Disposition'] = 'attachment; filename=kioskCode.zip'
                    f.close()
                    return response
                except Kiosk.DoesNotExist:
                    return HttpResponse("Kiosk '"+request.POST['kiosk_name']+"' not found")
    return HttpResponse('missing post data')

#Sends an SSH command to a kiosk telling it to update its code
#@login_required
#def forceUpdateCode(request,kiosk_id):
#    if isKioskAdmin(request.user):
#        k = get_object_or_404(Kiosk,pk=kiosk_id)
#        cmd = "ssh pi@"+k.ip+" '/usr/local/kiosk/updateCode.sh'"
#        retcode = subprocess.call(cmd,shell=True)
#        return HttpResponse(retcode)
#    else:
#        return HttpResponseRedirect(reverse('mpulse_site.views.login_prompt'))

#Displays a kiosk log
@login_required
@user_passes_test(isKioskAdmin)
def viewKioskLog(request,kiosk_id):
    k = get_object_or_404(Kiosk,pk=kiosk_id)
    if request.user in k.owners.all():
        if k.logFile:
            logTextLines = re.split('[\\r\\n(\\r\\n)]',k.logFile.read())
        else:
            logTextLines = ['No log file to display']
        return render_to_response('kioskLog.html',{'kiosk':k,'logTextLines':logTextLines},context_instance=RequestContext(request))
    #else:
        raise PermissionDenied
        #return HttpResponseRedirect(reverse('mpulse_site.views.login_prompt'))
    
#Renders a form for editing a kiosk
@login_required
@user_passes_test(isKioskAdmin)
def editKiosk(request,kiosk_id):
    k = get_object_or_404(Kiosk,pk=kiosk_id)
    if request.user in k.owners.all():
        if request.method == 'POST': # If form already submitted
            #bound forms
            registrationForm = KioskRegistrationForm(data = request.POST,instance=k) 
            if registrationForm.is_valid(): # All validation rules pass
                kiosk = registrationForm.save()
                message = "Kiosk succesfully edited. Note: If you changed your kiosk name, you will have to also change the name in your kiosk's kiosk_name.txt file in /usr/local/kiosk"
                
                return render_to_response('editKiosk.html',{'kiosk':k,'registrationForm':registrationForm,'message':message,'message_class':'success'},context_instance=RequestContext(request))
        else: #unbound forms
            registrationForm = KioskRegistrationForm(instance=k)
        
        return render_to_response('editKiosk.html',{'kiosk':k,'registrationForm':registrationForm},context_instance=RequestContext(request))
    
    else:
        raise PermissionDenied
        #return HttpResponseRedirect(reverse('mpulse_site.views.login_prompt'))
        
    

#Add an owner to a kiosk
@sensitive_variables('userByEmail')
@sensitive_post_parameters('email')
@login_required
@user_passes_test(isKioskAdmin)
def addKioskOwner(request,kiosk_id):
    k = get_object_or_404(Kiosk,pk=kiosk_id)
    registrationForm = KioskRegistrationForm(instance=k)
    if request.user in k.owners.all():
        if request.method == "POST" and 'email' in request.POST:
            try: #Try to find the user
                userByEmail = User.objects.get(email=request.POST['email'].strip())
            except User.DoesNotExist:
                message = "Unable to perform requested action: a user with the email "+request.POST['email'].strip()+" does not exist in our system"
                return render_to_response('editKiosk.html',{'kiosk':k,'registrationForm':registrationForm,'message':message,'message_class':'error'},context_instance=RequestContext(request))
            #Add the user as an owner
            k.owners.add(userByEmail)
            message = "User succesfully added as an owner"
            return render_to_response('editKiosk.html',{'kiosk':k,'registrationForm':registrationForm,'message':message,'message_class':'success'},context_instance=RequestContext(request))
        else:
            return HttpResponseRedirect(reverse('mpulse_site.views.editKiosk',args=(k.pk,)))
    else:
        raise PermissionDenied
        #return HttpResponseRedirect(reverse('mpulse_site.views.login_prompt'))
#Remove an owner from a kiosk
@sensitive_variables('owner')
@login_required
@user_passes_test(isKioskAdmin)
def removeKioskOwner(request,kiosk_id,owner_id):
    k = get_object_or_404(Kiosk,pk=kiosk_id)
    registrationForm = KioskRegistrationForm(instance=k)
    if request.user in k.owners.all():
        try:
            owner = User.objects.get(pk=owner_id)
        except User.DoesNotExist:
            message = "Unable to perform requested action: The user you were trying to remove as an owner no longer exists in our system"
            return render_to_response('editKiosk.html',{'kiosk':k,'registrationForm':registrationForm,'message':message,'message_class':'error'},context_instance=RequestContext(request))
        #Remove the owner if there is more than one owner
        if k.owners.count() > 1:
            k.owners.remove(owner)
            message = "Owner succesfully removed"
            message_class = "success"
        else:
            message = "Unable to perform requested action: Every kiosk must have at least one owner"
            message_class = "error"
        
        return render_to_response('editKiosk.html',{'kiosk':k,'registrationForm':registrationForm,'message':message,'message_class':message_class},context_instance=RequestContext(request))
    else:
        raise PermissionDenied
        #return HttpResponseRedirect(reverse('mpulse_site.views.login_prompt'))

##################################### DOCS ############################################
#Serves a private file for download
@login_required
@user_passes_test(isKioskAdmin)
def downloadPrivateFile(request,filename):
    loc = settings.ABS_PATH_TO_FILES+'/privateFiles/'+filename
    content = get_file_contents(loc)
    #Serve the file
    response = HttpResponse(content)
    response['Content-Disposition'] = 'attachment; filename='+filename
    return response
 
##################################### Custom 403/404/500 Pages ############################################
def custom_403_view(request):
    return render_to_response('403.html',{},context_instance=RequestContext(request))

def custom_404_view(request):
    return render_to_response('404.html',{},context_instance=RequestContext(request))

def custom_500_view(request):
    #Store the 500 in the db
    er = ExceptionReporter(request, *sys.exc_info())
    html = er.get_traceback_html()
    error = ServerError(html=html)
    error.save()
    
    #Return 500 error page
    response = render(request, "500.html")
    response.status_code = 500
    return response

##################################### Error Viewing ############################################
#Renders the page containing a list of current errors in the database
@login_required
@staff_member_required
def errorsList(request):
    errors = ServerError.objects.all()
    return render_to_response('errorList.html',{'errors':errors},context_instance=RequestContext(request))

#Returns the rendered 500 page html 
@login_required
@staff_member_required
def getErrorPage(request):
    if request.method == "GET" and 'id' in request.GET:
        error_id = request.GET['id']
    else:
        return HttpResponse('Unable to retrieve error contents')
    
    error = get_object_or_404(ServerError,pk=error_id)
    return HttpResponse(error.html)

#Deletes a server error
@login_required
@staff_member_required
def deleteError(request,error_id):
    error = get_object_or_404(ServerError,pk=error_id)
    error.delete()
    return HttpResponseRedirect(reverse('mpulse_site.views.errorsList'))

##################################### TEST ############################################
@sensitive_variables('b')
def test(request):
    a = 1
    b = 2
    x = 5 / 0
    return HttpResponse('error')
