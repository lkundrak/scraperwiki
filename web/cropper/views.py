from django.template import RequestContext
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.core.urlresolvers import reverse
import re, os, urlparse, urllib, cStringIO
import tempfile, shutil
import Image, ImageDraw, ImageEnhance, ImageChops

import logging
logger = logging

#There is an API  http://tinyurl.com/api-create.php?url='.$u
# need a form that submits and makes this possible.  (checking it's for a PDF as well)

"""Creator:        TOSHIBA e-STUDIO520
Producer:       MFPImgLib V1.0
CreationDate:   Wed May 20 08:17:33 2009
Tagged:         no
Pages:          48
Encrypted:      no
File size:      1100938 bytes
Optimized:      no
PDF version:    1.3"""

# Until recently was able to return file objects to HttpResponse, but this stopped 
# working, so now need to read in the stream into a string object before returning.  
# Baffling.  May be related to how the CSV streaming ceased working where the 
# middle-ware began consuming the stream to measure the content-length and then there was 
# nothing left to send out.

# for future ref this is likely gzip middleware, which can't work until it knows how much 
# data it is going to be compressing - ross.

dkpercent = 83  # percentage darkness used by the cropper

def pdfinfo(pdffile):
    cmd = 'pdfinfo "%s"' % pdffile
    result = { }
    for line in os.popen(cmd).readlines():
        try:
            c = line.index(':')
        except ValueError:
            continue
        key = line[:c].replace(" ", "")
        value = line[c+1:].strip()
        if key == "Pages":
            value = int(value)
        result[key] = value
    return result
        
        
def ParseSortCropping(cropping):
    if not cropping:
        cropping = ""
    croppings = [ ]
    clippings = [ ]
    for crop in cropping.split("/"):
        mhr = re.match('(rect|clip)_(\d+),(\d+)_(\d+),(\d+)$', crop)
        if mhr:
            if mhr.group(1) == "rect":
                croppings.append(crop)
            else:
                clippings.append(crop)
    if len(clippings) >= 2:
        del clippings[:-1]
    croppings = croppings + clippings
    newcropping = "/".join(croppings)
    if newcropping:
        newcropping += '/'
    return croppings, newcropping
        
        
def cropdoc(request):
    url = request.GET.get("url")
    if not url:
        return HttpResponseRedirect(reverse('croppage', args=['t.2wk7srh', 1])) 
    
    return HttpResponseRedirect("%s?url=%s" % (reverse('croppage', args=['u', 1]), urllib.quote(url))) 
    
def GetSrcDoc(request, srcdoc):
    url = request.GET.get("url")
    if srcdoc[:2] == 't.':
        pdfurl = urlparse.urljoin("http://tinyurl.com/", srcdoc[2:])
        pdffile = os.path.join(settings.CROPPER_SOURCE_DIR, "%s.pdf" % srcdoc)
        imgstem = os.path.join(settings.CROPPER_IMG_DIR, srcdoc)
        qtail = ""
    elif srcdoc == "u" and url:
        pdfurl = url
        lsrcdoc = pdfurl.replace('/', '|')
        pdffile = os.path.join(settings.CROPPER_SOURCE_DIR, lsrcdoc)
        imgstem = os.path.join(settings.CROPPER_IMG_DIR, lsrcdoc)
        qtail = "?%s" % urllib.urlencode({"url":pdfurl})
    else:
        pdfurl, pdffile, imgstem, qtail = None, None, None, None
        
    return pdfurl, pdffile, imgstem, qtail
        
        
def croppage(request, srcdoc, page, cropping):
    page = int(page)
    croppings, cropping = ParseSortCropping(cropping)
    
    pdfurl, pdffile, imgstem, qtail = GetSrcDoc(request, srcdoc)
    if not pdfurl:
        return HttpResponseRedirect(reverse('croppage', args=['t.2wk7srh', 1])) 
        
    if not os.path.isfile(pdffile):  # download file if it doesn't exist
        tpdffile = tempfile.NamedTemporaryFile(suffix='.pdf')
        try:
            filename, headers = urllib.urlretrieve(pdfurl, tpdffile.name)
        except ValueError, e:
            return HttpResponse("Error fetching: %s; %s" % (pdfurl, str(e)))
        except IOError, e:
            return HttpResponse("Error fetching: %s; %s" % (pdfurl, str(e)))
        if headers.subtype != 'pdf':
            return HttpResponse("%s is not pdf type; it's \"%s\"" % (pdfurl, headers.subtype))
        #print (tpdffile.name, pdffile)
        shutil.copy(tpdffile.name, pdffile)
    
    data = { "page":int(page), "srcdoc":srcdoc, "cropping":cropping, "qtail":qtail, "pdfurl":pdfurl, "MAIN_URL":settings.MAIN_URL }
    data.update(pdfinfo(pdffile))
    
    data["losecroppings"] = [ ]
    if len(croppings) > 1:
        for i, lcropping in enumerate(croppings):
            data["losecroppings"].append(("%d"%(i+1), '/'.join([ llcropping  for llcropping in croppings  if llcropping != lcropping ])+'/'))
    if len(croppings) > 0:
            data["losecroppings"].append(("All", ""))
    
    if page > 1:
        data["prevpage"] = min(page-1, data["Pages"])
    if page < data["Pages"]:
        data["nextpage"] = max(page+1, 1)
    
    return render_to_response('cropper/cropperpage.html', data, context_instance=RequestContext(request))


   
   # this can send out jpgs if the png versions are too big
pngfilesizeconsiderlimit = 200000
pngfilesizejpgfactor = 5

def cropimg(request, format, srcdoc, page, cropping):
    page = int(page)
    cropping = cropping or ""

    pdfurl, pdffile, imgstem, qtail = GetSrcDoc(request, srcdoc)
    # It is possible that imgstem is None.
    if (not pdfurl) or (not imgstem):
        return HttpResponse(open(os.path.join(settings.MEDIA_DIR, 'images', '404.png'), "rb").read(), mimetype='image/png')

    if not os.path.isfile(pdffile):
            # possibly should download it
        return HttpResponse(open(os.path.join(settings.MEDIA_DIR, 'images', '404.png'), "rb").read(), mimetype='image/png')

    imgfile = "%s_%04d.png" % (imgstem, page)
    imgpixwidth = 800
    
    if not os.path.isfile(imgfile):
        cmd = 'convert -quiet -density 192 "%s[%d]" -resize %d -define png:color-type=2 "%s" > /dev/null 2>&1' % (pdffile, page-1, imgpixwidth, imgfile)
        os.system(cmd)

    croppings = filter(lambda x:x, cropping.split("/"))
    
    if not croppings:
        if os.path.getsize(imgfile) > pngfilesizeconsiderlimit:
            jpgimgfile = "%s_%04d.jpg" % (imgstem, page)
            if not os.path.isfile(jpgimgfile):
                cmd = 'convert -quiet -density 192 "%s[%d]" -resize %d "%s" > /dev/null 2>&1' % (pdffile, page-1, imgpixwidth, jpgimgfile)
                os.system(cmd)
            #print "\n\njpg/png sizes", os.path.getsize(jpgimgfile), os.path.getsize(imgfile)
            if os.path.getsize(jpgimgfile) < os.path.getsize(imgfile) / pngfilesizejpgfactor:
                return HttpResponse(open(jpgimgfile, "rb").read(), mimetype='image/jpeg')
        return HttpResponse(open(imgfile, "rb").read(), mimetype='image/png')


    # png images began causing problems by loading in mode="I" instead of mode="RGB"
    # fixed with the -define png:color-type=2 setting above

    # here on is executed only if there is a cropping to be applied
    pfp = Image.open(imgfile)    
    #pfp = Image.open(jpgimgfile)
    swid, shig = pfp.getbbox()[2:]
    
    highlightrects = [ ]
    clip = None
    for crop in croppings:
        mhr = re.match('(rect|clip)_(\d+),(\d+)_(\d+),(\d+)$', crop)
        if mhr:
            dim = (int(mhr.group(2))*swid/1000, int(mhr.group(3))*swid/1000, int(mhr.group(4))*swid/1000, int(mhr.group(5))*swid/1000)
            if mhr.group(1) == "rect":
                highlightrects.append(dim)
            if mhr.group(1) == "clip":
                clip = dim
        
        
    # build the mask which is a darker version of the original
    # then plots white rectangle over it, which when ImageChops.darker() is applied 
    # between the two favours the lighter original in instead of the white rectangles
    if highlightrects:
        # print pfp.mode  must not be I
        dpfp = ImageEnhance.Brightness(pfp).enhance(dkpercent / 100.0)
        ddpfp = ImageDraw.Draw(dpfp)
        for rect in highlightrects:
            ddpfp.rectangle(rect, (255, 255, 255))
        cpfp = ImageChops.darker(pfp, dpfp) # makes darker of the two
    else:
        cpfp = pfp

    # pngprev is about whether the crop is applied or is masked so you can see it in place
    if clip:
        if format == "pngprev":
            p1 = Image.new("RGB", (swid, shig))
            dp1 = ImageDraw.Draw(p1)
            dp1.rectangle((0,0,swid,shig), (155, 10, 10))
            dp1.rectangle(clip, (255, 255, 255))
            cpfp = ImageChops.darker(p1, cpfp) # makes darker of the two
        else:
            cpfp = cpfp.crop(clip)
    
    # actually if the png version is WAY too large we revert to giving you a jpg because it's probably a dirty scan
    imgmimetype ='image/png'
    imgout = cStringIO.StringIO()
    cpfp.save(imgout, "png")
    
    if imgout.tell() > pngfilesizeconsiderlimit:
        jpgimgout = cStringIO.StringIO()
        
# Problem - We need horsell to have jpeg writer installed
        try:  
            cpfp.save(jpgimgout, "jpeg")
            if jpgimgout.tell() < imgout.tell() / pngfilesizejpgfactor:
                imgout = jpgimgout
                imgmimetype = 'image/jpeg'
        except IOError, e:
            logging.warning(str(e.args))
            assert e.args[0] == 'encoder jpeg not available', e.args

    imgout.reset()
    return HttpResponse(imgout.read(), mimetype=imgmimetype)

