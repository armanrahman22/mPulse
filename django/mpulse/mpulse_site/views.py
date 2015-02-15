from django.http import HttpResponse,HttpResponseRedirect
from django.core.urlresolvers import reverse

from django.shortcuts import render_to_response, get_object_or_404, get_list_or_404
from django.template.loader import render_to_string

from django.template import RequestContext

from django.contrib.auth import authenticate, login, logout

from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt, csrf_protect

from mpulse_site.models import Kiosk, Session, UserProfile, UserForm,UserProfileForm, EditUserForm
from django.contrib.auth.models import User

from datetime import date,datetime
from time import strptime,mktime
from django.utils import timezone
from django.utils.dateformat import DateFormat

from django.core.mail import EmailMessage, send_mail

from util import sessionPDF

from django.conf import settings

    
######################### INDEX / HELP ####################################

def index(request):
    return render_to_response('index.html',context_instance=RequestContext(request));
    
def help(request):
    return render_to_response('help.html',context_instance=RequestContext(request));
    
######################## LOGIN / LOGOUT #################################

#Login page
def login_prompt(request):
    return render_to_response('login.html',context_instance=RequestContext(request))

#Login function - redirects to dashboard
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
            
            return HttpResponseRedirect(reverse('mpulse_site.views.help')) # Redirect after creation to help page
    else: #unbound forms
        userForm = UserForm()
        userProfileForm = UserProfileForm()
        
    return render_to_response('createAccount.html',{'userForm':userForm,'userProfileForm':userProfileForm,'tmp_username':tmp_username},context_instance=RequestContext(request))

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

def setup_account(request):
    pass

#Shows a user profile (may look different depending on who is accessing it)
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
@login_required
def session(request,session_id):
    session = get_object_or_404(Session,pk=session_id) #Get session by id number or raise 404 if doesn't exist
    if session.user == request.user: #if session belongs to the current user
        graphData = eval(session.graphData)
        ecgData = [[x[0]/10.0**6,x[1]] for x in graphData['ecg']]
        return render_to_response('session.html',{'session':session,'sessionData':eval(session.sessionData),'ecgData':ecgData},context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect(reverse('mpulse_site.views.login_prompt'),context_instance=RequestContext(request))

@login_required
def emailSession(request,session_id):
    session = get_object_or_404(Session,pk=session_id) #Get session by id number or raise 404 if doesn't exist
    if session.user == request.user: #if session belongs to the current user
        graphData = eval(session.graphData)
        ecgData = [[x[0]/10.0**6,x[1]] for x in graphData['ecg']]
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
        return HttpResponseRedirect(reverse('mpulse_site.views.login_prompt'),context_instance=RequestContext(request))
    
@login_required
def exportSession(request,session_id):
    session = get_object_or_404(Session,pk=session_id) #Get session by id number or raise 404 if doesn't exist
    if session.user == request.user: #if session belongs to the current user
        graphData = eval(session.graphData)
        ecgData = [[x[0]/10.0**6,x[1]] for x in graphData['ecg']]
        buffer = sessionPDF(session.user.get_full_name(),timezone.localtime(session.datetime_taken),session.kiosk.location,eval(session.sessionData),ecgData)
        fileContents = buffer.getvalue()
        buffer.close()
    
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="SessionResults.pdf"'
        response.write(fileContents)
        return response
    else:
        return HttpResponseRedirect(reverse('mpulse_site.views.login_prompt'),context_instance=RequestContext(request))
    
@csrf_exempt
def saveSessionData(request):
    if request.method == "POST":
            if 'kioskName' in request.POST and 'userEmail' in request.POST and 'datetimeTaken' in request.POST and 'sessionData' in request.POST and 'graphData' in request.POST and 'secret_key' in request.POST:
                try: #Get kiosk if it exists
                    kiosk = Kiosk.objects.get(name=request.POST['kioskName'])
                except Kiosk.DoesNotExist:
                    return HttpResponse('failure: kiosk does not exist')
                
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
                return HttpResponse('success')
    return HttpResponse('no or imcomplete data')           
                
@csrf_exempt
def emailSessionData(request):
    if request.method == "POST":
            if 'kioskName' in request.POST and 'userEmail' in request.POST and 'datetimeTaken' in request.POST and 'sessionData' in request.POST and 'graphData' in request.POST and 'secret_key' in request.POST:
                try: #Get kiosk if it exists
                    kiosk = Kiosk.objects.get(name=request.POST['kioskName'])
                except Kiosk.DoesNotExist:
                    return HttpResponse('failure: kiosk does not exist')
                
                #Check to make sure the secret key matches the one sent from the kiosk on registration
                if kiosk.secret_key.strip() != request.POST['secret_key'].strip():
                    return HttpResponse('verification failure')
                
                #create and email a pdf of the data to the user
                graphData = eval(request.POST['graphData'])
                if 'ecg' in graphData:
                    ecgData = [[x[0]/10.0**6,x[1]] for x in graphData['ecg']]
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
@login_required
def chartHeight(request):
    data = [
        ['Date', 'Height (ft)'],
    ]
    for session in request.user.session_set.exclude(sessionData__isnull=True).order_by('datetime_taken'):
        height = None
        for item in eval(session.sessionData):
            if item[0] == 'Height':
                height = item[1]
        if height:
            data += [[timezone.localtime(session.datetime_taken).strftime('%m/%d/%Y'),height]]
    
    if request.user.get_profile().height:
        data += [['Today',float(str(request.user.get_profile().height))]]
    
    return render_to_response('lineChart.html',{'title':'Height Chart','data':data},context_instance=RequestContext(request));

@login_required
def chartWeight(request):
    data = [
        ['Date', 'Weight (lbs)'],
    ]
    for session in request.user.session_set.exclude(sessionData__isnull=True).order_by('datetime_taken'):
        weight = None
        for item in eval(session.sessionData):
            if item[0] == 'Weight':
                weight = item[1]
        if weight:
            data += [[timezone.localtime(session.datetime_taken).strftime('%m/%d/%Y'),weight]]
    
    if request.user.get_profile().weight:
        data += [['Today',float(str(request.user.get_profile().weight))]]
    
    return render_to_response('lineChart.html',{'title':'Weight Chart','data':data},context_instance=RequestContext(request));

@login_required
def chartBMI(request):
    data = [
        ['Date', 'BMI'],
    ]
    for session in request.user.session_set.exclude(sessionData__isnull=True).order_by('datetime_taken'):
        weight,height = None,None
        for item in eval(session.sessionData):
            if item[0] == 'Weight':
                weight = item[1]
            if item[0] == 'Height':
                height = item[1]
        if weight and height:
            height = height * 12
            h = height**2
            bmi = weight / h * 703
            data += [[timezone.localtime(session.datetime_taken).strftime('%m/%d/%Y'),float(format(bmi,'.2f'))]]
        
    if request.user.get_profile().weight and request.user.get_profile().height:
        height = request.user.get_profile().height * 12
        h = height**2
        bmi = request.user.get_profile().weight / h * 703
        data += [['Today',float(format(bmi,'.2f'))]]
    
    return render_to_response('lineChart.html',{'title':'BMI Chart','data':data},context_instance=RequestContext(request));
    
################################ KIOSKS / MANAGE######################################
def kiosks(request):              
    kiosks = Kiosk.objects.all()
    for kiosk in kiosks:
        kiosk.checkForOffline()
    lats,lngs = [kiosk.gpsLocLat for kiosk in kiosks if kiosk.gpsLocLat],[kiosk.gpsLocLong for kiosk in kiosks if kiosk.gpsLocLong]
    if len(lats) > 0 and len(lngs) > 0:    
        center = (sum(lats)/len(lats),sum(lngs)/len(lngs))
    else:
        center = (0,0)
    return render_to_response('kiosks.html',{'kiosks':kiosks,'center':center},context_instance=RequestContext(request));

def kiosksXML(request):
    kiosks = Kiosk.objects.exclude(gpsLocLat__isnull=True).exclude(gpsLocLong__isnull=True)
    for kiosk in kiosks:
        kiosk.checkForOffline()
    return render_to_response('kiosk_list_XML.xml',{'kiosks':kiosks})

        
@csrf_exempt
def manage(request):
        if request.method == "POST":
            if 'pi_name' in request.POST and 'ip' in request.POST and 'old_secret_key' in request.POST and 'new_secret_key' in request.POST: #and 'location' in request.POST:
                try:
                    k = Kiosk.objects.get(name=request.POST['pi_name'])
                    if k.secret_key != request.POST['old_secret_key']: #Check for correct secret key
                        return HttpResponse('verification failure')
                    k.ip = request.POST['ip'].strip()
                    k.secret_key = request.POST['new_secret_key'].strip()
                    #k.location = request.POST['location']
                except Kiosk.DoesNotExist: #Make a new kiosk if this is the first time one tries to connect
                    k = Kiosk(name=request.POST['pi_name'],ip=request.POST['ip'].strip(),secret_key=request.POST['new_secret_key'].strip())#,location=request.POST['location'])
                    
                k.status = 'O'
                k.lastCheckIn = timezone.now()
                k.save()
                return HttpResponse('success')
                
        elif request.user.is_authenticated() and request.user.is_staff:                
            kiosks = Kiosk.objects.all()
            for kiosk in kiosks:
                kiosk.checkForOffline()
            return render_to_response('manage.html',{'kiosks':kiosks},context_instance=RequestContext(request));
        else:
            return HttpResponseRedirect(reverse('mpulse_site.views.login_prompt'))
        
##################################### TEST ############################################
        
def test(request):
    send_mail('M-PULSE Kiosk Session Results Waiting', 'This message is to inform you that an account has been created for you at '+settings.DOMAIN+settings.SITE_ROOT+'/ and that you have session results saved there. Please go to '+settings.DOMAIN+reverse('password_reset')+' to set a password for your account.', settings.DEFAULT_FROM_EMAIL,  ['maby@mit.edu'], fail_silently=False)
    return HttpResponse('email sent')
    #subject = 'M-Pulse Kiosk Session Results'
    #message = 'Contents'
    #sender = settings.DEFAULT_FROM_EMAIL
    #recipients = ['wddc93@gmail.com']
    #email = EmailMessage(subject,message,sender,recipients,headers={'Reply-To':sender})
    #sessionData = [['Skin Temperature',96.8,u'\xb0'+' F'],['Pulse Rate',65,' BPM'],['Percent Saturation of Oxygen in the Blood',98,'%']]
    #ecgData = [[6357428,1.70577],[6375108,1.64712],[6392788,1.62268],[6410468,1.60313],[6428148,1.64223],[6445828,1.65689],[6463512,1.69110],[6481188,1.69110],[6498868,1.68133],[6516548,1.71554],[6534228,1.67644],[6551908,1.71554],[6569588,1.71554],[6587268,1.73998],[6604948,1.79863],[6622628,1.82796],[6640308,1.67644],[6657988,1.69110],[6675668,1.69110],[6693348,1.65200],[6711028,1.91105],[6728712,2.26295],[6746388,1.47116],[6764068,1.58847],[6781748,1.64712],[6799428,1.73509],[6817108,1.80841],[6834788,1.79863],[6852468,1.79374],[6870148,1.79374],[6887828,1.87683],[6905508,1.89638],[6923184,2.00391],[6940868,1.97947],[6958548,1.84262],[6976228,1.80352],[6993908,1.72532],[7011588,1.74976],[7029268,1.73021],[7046948,1.65200],[7064628,1.70088],[7082308,1.74976],[7099988,1.77908],[7117668,1.77419],[7135348,1.73021],[7153028,1.82307],[7170708,1.74487],[7188388,1.77908],[7206076,1.73021],[7223748,1.86217],[7241428,1.80352],[7259108,1.69599],[7276788,1.74487],[7294468,1.70577],[7312148,1.79863],[7329836,1.95992],[7347508,2.21408],[7365188,1.48583],[7382868,1.61779],[7400548,1.81818],[7418228,1.81818],[7435908,1.85239],[7453588,1.88172],[7471276,1.79863],[7488948,1.91593],[7506628,1.92082],[7524308,1.93548],[7541988,1.99902],[7559668,1.90616],[7577348,1.93060],[7595036,1.72043],[7612708,1.74976],[7630388,1.69599],[7648068,1.66667],[7665748,1.73998],[7683428,1.73509],[7701108,1.76931],[7718788,1.80841],[7736468,1.79374],[7754148,1.79863],[7771828,1.83773],[7789508,1.81329],[7807188,1.90127],[7824868,1.87683],[7842548,1.85728],[7860232,1.79374],[7877908,1.84751],[7895588,1.78886],[7913268,1.89638],[7930948,2.17986],[7948628,1.91593],[7966308,1.57869],[7983988,1.84751],[8001668,1.84751],[8019348,1.90616],[8037028,1.84262],[8054708,1.85239],[8072388,1.93060],[8090068,1.93548],[8107748,1.99413],[8125428,1.94526],[8143108,1.99902],[8160788,1.86706],[8178468,1.93060],[8196148,1.79863],[8213828,1.78397],[8231508,1.72043],[8249188,1.77908],[8266868,1.80352],[8284548,1.81818],[8302228,1.81818],[8319908,1.81329],[8337596,1.76931],[8355268,1.84751],[8372948,1.83284],[8390628,1.87683],[8408308,1.83284],[8425988,1.88172],[8443668,1.75464],[8461356,1.74487],[8479028,1.73998],[8496708,1.69599],[8514388,1.78397],[8532064,2.06256],[8549748,1.96481],[8567428,1.49071],[8585108,1.60802],[8602796,1.73509],[8620468,1.72532],[8638148,1.74976],[8655828,1.76931],[8673508,1.75953],[8691188,1.79374],[8708868,1.83284],[8726552,1.82307],[8744228,1.84751],[8761908,1.81329],[8779588,1.72043],[8797268,1.67644],[8814948,1.59824],[8832628,1.59335],[8850308,1.66178],[8867988,1.63734],[8885668,1.73509],[8903348,1.70088],[8921028,1.78886],[8938708,1.71554],[8956388,1.83284],[8974068,1.78886],[8991752,1.79863],[9009428,1.82307],[9027108,1.90127],[9044788,1.97947],[9062468,1.77419],[9080148,1.88661],[9097828,1.84262],[9115508,1.86706],[9133188,1.95503],[9150868,2.16031],[9168548,2.35093],[9186228,1.64223],[9203908,1.90127],[9221588,1.91105],[9239264,2.02835],[9256944,2.06745],[9274624,2.09677],[9292304,2.07234],[9309988,2.19453],[9327668,2.17498],[9345348,2.30694],[9363028,2.28739],[9380704,2.31672],[9398388,2.23363],[9416068,2.18475],[9433744,2.10166],[9451428,2.10655],[9469112,2.10166],[9486784,2.04301],[9504468,2.05767],[9522148,2.11632],[9539828,2.13587],[9557504,2.10166],[9575188,2.15054],[9592872,2.18964],[9610548,2.22385],[9628228,2.17009],[9645908,2.17498],[9663588,2.13587],[9681268,2.17009],[9698948,2.24340],[9716624,2.14076],[9734312,2.14076],[9751984,2.10166],[9769664,2.06256],[9787348,2.23851],[9805028,2.43891],[9822708,2.36070],[9840388,1.86706],[9858072,2.04790],[9875748,2.11632],[9893428,2.14565],[9911108,2.20919],[9928788,2.24340],[9946468,2.19941],[9964148,2.22874],[9981824,2.18964],[9999508,2.21408],[10017188,2.19941],[10035908,2.21408],[10054624,2.10166],[10073344,2.01369],[10092068,1.90616],[10110788,1.82796],[10129508,1.93548],[10148228,1.91105],[10166948,1.92082],[10185668,1.94526],[10204384,2.02346],[10223108,1.98436],[10241828,1.98436],[10260548,1.88172],[10279268,1.86217],[10297988,1.84751],[10316708,1.82796],[10335428,1.86706],[10354148,1.97458],[10372868,1.85728],[10391592,1.83284],[10410308,1.85239],[10429028,1.83284],[10447748,1.88661],[10466476,2.19453],[10485188,1.79863],[10503908,1.56892],[10522632,1.75953],[10541348,1.78397],[10560068,1.76931],[10578788,1.82307],[10597508,1.76442],[10616228,1.83773],[10634948,1.85728],[10653668,1.94526],[10672388,1.87683],[10691108,1.90616],[10709828,1.79863],[10728548,1.72532],[10747268,1.71065],[10765988,1.64712],[10784708,1.66178],[10803428,1.63245],[10822148,1.77908],[10840868,1.77908],[10859588,1.70088],[10878308,1.72532],[10897028,1.65689],[10915748,1.74976],[10934468,1.70577],[10953188,1.73998],[10971908,1.63245],[10990632,1.76931],[11009348,1.74976],[11028068,1.73021],[11046788,1.68133],[11065516,1.70088],[11084228,1.66178],[11102948,1.72532],[11121676,1.92082],[11140388,1.79374],[11159108,1.41251],[11177828,1.55914],[11196548,1.57380],[11215268,1.64223],[11233988,1.64223],[11252708,1.66667],[11271428,1.73509],[11290148,1.78886],[11308868,1.81329],[11327588,1.78397],[11346308,1.79863],[11365028,1.76931],[11383748,1.77908],[11402468,1.72043],[11421188,1.68133],[11439908,1.65689],[11458628,1.65689],[11477348,1.71554],[11496068,1.69110],[11514788,1.74487],[11533508,1.73998],[11552228,1.65689],[11570948,1.67155],[11589676,1.72532],[11608388,1.70088],[11627108,1.68622],[11645828,1.67644],[11664556,1.73998],[11683268,1.79863],[11701988,1.66178],[11720716,1.69110],[11739428,1.65200],[11758148,1.63245],[11776868,1.74976],[11795584,2.01369],[11814308,1.85728],[11833028,1.43695],[11851748,1.56403],[11870468,1.69599],[11889188,1.68133],[11907908,1.69599],[11926628,1.59824],[11945348,1.64712],[11964068,1.74487],[11982788,1.79374],[12001508,1.76442],[12020228,1.71554],[12038948,1.84262],[12057668,1.73509],[12076388,1.66667],[12095108,1.59824],[12113828,1.66178],[12132548,1.64712],[12151268,1.71065],[12169988,1.68622],[12188716,1.73021],[12207428,1.72532],[12226148,1.63245],[12244868,1.72043],[12263596,1.67155],[12282308,1.74976],[12301028,1.72532],[12319752,1.69599],[12338468,1.73021],[12357188,1.75953],[12375908,1.83284],[12394628,1.70577],[12413348,1.72043],[12432068,1.67644],[12450788,1.72043],[12469508,1.82796],[12488228,2.20919],[12506948,1.48094],[12525668,1.51026],[12544388,1.68622],[12563108,1.69599],[12581828,1.75464],[12600548,1.76931],[12619268,1.85239],[12637988,1.83284],[12656708,1.89638],[12675428,1.89638],[12694148,1.83284],[12712868,1.89150],[12731588,1.83773],[12750308,1.73021],[12769028,1.61779],[12787752,1.55914],[12806468,1.55425],[12825188,1.59335],[12843908,1.60802],[12862636,1.65200],[12881348,1.69599],[12900068,1.66667],[12918792,1.67644],[12937508,1.70577],[12956228,1.78886],[12974948,1.82796],[12993668,1.82796],[13012388,1.86706],[13031108,1.96970],[13049824,2.07234],[13068548,1.95015],[13087268,1.90127],[13105988,1.82796],[13124708,1.83773],[13143428,1.85239],[13162148,2.22874],[13180868,2.20919],[13199588,1.71554],[13218308,1.95015],[13237024,2.00880],[13255748,1.99902],[13274464,2.04790],[13293184,2.03324],[13311908,1.95503],[13330628,1.78397],[13349348,1.78397],[13368068,1.74487],[13386796,1.77908],[13405508,1.76442],[13424228,1.68133],[13442948,1.59824],[13461676,1.52004],[13480388,1.59824],[13499108,1.64712],[13517832,1.65689],[13536548,1.74976],[13555268,1.69110],[13573988,1.70088],[13592708,1.73509],[13611428,1.78397],[13630148,1.77908],[13648868,1.76442],[13667588,1.75953],[13686308,1.73998],[13705028,1.84262],[13723748,1.81329],[13742468,1.73998],[13761188,1.81818],[13779908,1.79863],[13798628,1.84751],[13817348,1.96481],[13836068,2.30205],[13854788,1.51026],[13873508,1.70088],[13892228,1.76442],[13910948,1.75464],[13929668,1.87195],[13948388,1.87683],[13967108,1.90616],[13985836,1.95015],[14004548,1.87683],[14023264,2.01369],[14041988,1.95503],[14060712,2.00880],[14079428,1.86706],[14098148,1.80841],[14116876,1.71554],[14135588,1.77908],[14154308,1.78397],[14173028,1.79863],[14191748,1.83773],[14210468,1.81329],[14229188,1.92082],[14247908,1.93060],[14266628,1.85728],[14285348,1.84262],[14304068,1.78397],[14322788,1.83773],[14341508,1.93060],[14360228,1.85239],[14378948,1.79374],[14397668,1.83284],[14416388,1.77908],[14435108,1.90616],[14453828,2.22874],[14472548,1.63734],[14491268,1.61290],[14509988,1.81818],[14528708,1.85728],[14547428,1.86706],[14566148,1.92571],[14584876,1.89638],[14603588,1.92571],[14622308,1.97458],[14641024,2.00391],[14659756,1.96481],[14678464,2.03324],[14697188,1.80841],[14715912,1.81329],[14734628,1.77908],[14753348,1.79374],[14772068,1.76442],[14790788,1.81818],[14809508,1.81329],[14828228,1.87195],[14846948,1.85239],[14865668,1.92082],[14884388,1.80352],[14903108,1.81329],[14921828,1.90127],[14940548,1.82796],[14959268,1.95015],[14977988,1.84262],[14996708,1.81818],[15015428,1.81818],[15034148,1.82307],[15052868,1.86217],[15071588,2.07722],[15090308,2.21896],[15109028,1.59335],[15127748,1.76442],[15146468,1.82796],[15165188,1.87195],[15183916,1.90616],[15202628,1.90127],[15221348,1.92571],[15240068,1.95015],[15258792,2.01857],[15277504,2.06256],[15296228,1.99902],[15314956,1.96970],[15333668,1.82307],[15352388,1.79374],[15371108,1.73509],[15389828,1.73509],[15408548,1.80352],[15427268,1.78886],[15445988,1.85728],[15464708,1.84262],[15483428,1.85728]]
    #buffer = sessionPDF('Maddy Aby',datetime.now(),'IDC',sessionData,ecgData)
    #fileContents = buffer.getvalue()
    #buffer.close()
    #email.attach('SessionResults.pdf',fileContents,'application/pdf')
    ##email.send(fail_silently=False)
    #
    #response = HttpResponse(content_type='application/pdf')
    #response['Content-Disposition'] = 'attachment; filename="SessionResults.pdf"'
    #response.write(fileContents)
    #return response

