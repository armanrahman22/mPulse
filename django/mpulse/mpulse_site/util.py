from os.path import exists

#PDF imports
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.graphics.shapes import Drawing,String
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics import renderPDF
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO

#Returns the filepath used for comment file uploads
def getSessionFilePath(instance,filename):
        return getUniquePath('sessions/'+instance.user.username+'/'+str(instance.datetime_taken)+'/'+filename)
            
def getUniquePath(path):
    root,end = path.rsplit('.',1)
    i = 2
    while exists(path):
        path = root+'_'+str(i)+'.'+end
        i += 1
    return path

####################### FILE UPLOAD/VIEW ############################
def handle_uploaded_file(f,destPath):
    with open(destPath, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

def get_file_contents(loc):
    serveFile = open(loc,'rb')
    contents = serveFile.read()
    serveFile.close()
    return contents


############### PDF Generation of Session Data #####################

#Session pdf generator
#Creates a PDF containing the given session data and 
# Returns a BytesIO() buffer containing the PDF
def sessionPDF(subjectName,sessionDate,location,sessionData,ecgData):
    width,height = letter
    leftMargin = 0.75*inch
    rightMargin = 0.75*inch
    topMargin = 0.75*inch
    bottomMargin = 0.75*inch
    
    rightBoundary = width - rightMargin
    topBoundary = height - topMargin
    
    font = "Helvetica"
    fontBold = "Helvetica-Bold"
    
    styles = getSampleStyleSheet()

    #Header with subject's name, date to put on every page
    def drawHeader(c,doc):
        c.saveState()
        c.setFont(font, 10)
        c.drawString(leftMargin,topBoundary,"M-Pulse Kiosk Session Results - "+subjectName)
        c.drawRightString(rightBoundary,topBoundary,sessionDate.strftime("%B %d %Y %I:%M%p"))
        c.line(leftMargin,topBoundary-0.1*inch,rightBoundary,topBoundary-0.1*inch) #Draw horizontal line on the page
        c.restoreState()
        
    #Creates a graph with ecgData and returns the Drawing object
    def ecgGraph(ecgData):
        ecgWidth,ecgHeight = 500, 200
        drawing = Drawing(ecgWidth,ecgHeight)
        #processedData = [[x[0]/10.0**6,x[1]] for x in ecgData] #Turn x-axis to seconds instead of microseconds
        data = [ecgData]
        lp = LinePlot()
        lp.x = 0
        lp.y = 0
        lp.height = ecgHeight
        lp.width = ecgWidth
        lp.data = data
        lp.joinedLines = 1
        lp.xValueAxis.labelTextFormat = '%2.1f'
        #lp.yValueAxis.valueMin = 0
        #lp.yValueAxis.valueMax = 5
        lp.yValueAxis.visible = False
        drawing.add(lp)
        drawing.add(String(ecgWidth/2,-25, 'Time (s)', fontSize=10))
        return drawing
    
        
    #Create draw and save PDF
    buffer = BytesIO()
    #Build up the document
    doc = SimpleDocTemplate(buffer,pagesize=letter,rightMargin=rightMargin,leftMargin=leftMargin-5)
    Elements = []
    #Add session data
    for item in sessionData:
        Elements.append(Paragraph("<b>"+item[0]+": </b>"+str(item[1])+item[2],styles["Normal"]))
    #Add EKG graph
    if ecgData != None:
        Elements.append(Paragraph("<b>ECG Graph: </b>",styles["Normal"]))
        Elements.append(Spacer(1,0.25*inch))
        Elements.append(ecgGraph(ecgData))
    Elements.append(Spacer(1,inch))
    #Closing paragraph
    Elements.append(Paragraph("Thank you for visiting the M-Pulse Kiosk at "+location+". Stay healthy!",styles["Normal"]))
    #Add the elements to the document
    doc.build(Elements, onFirstPage=drawHeader, onLaterPages=drawHeader)
    #c = canvas.Canvas(buffer,pagesize=letter)
    #draw(c)
    #c.save()
    return buffer