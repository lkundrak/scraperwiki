
function setupDataMap(oData, sUrl){

    // Setup the map
    oNavigation = new OpenLayers.Control.Navigation();
    oNavigation.zoomWheelEnabled = false;
    oPanZoomBar = new OpenLayers.Control.PanZoomBar();
    
    oMap = new OpenLayers.Map ("divDataMap", {
          controls:[
              oNavigation,
              oPanZoomBar,
              new OpenLayers.Control.Attribution()],
          maxExtent: new OpenLayers.Bounds(-20037508.34,-20037508.34,20037508.34,20037508.34),
          maxResolution: 156543.0399,
          numZoomLevels: 10,
          units: 'm',
          projection: new OpenLayers.Projection("EPSG:900913"),
          displayProjection: new OpenLayers.Projection("EPSG:4326")
    } );


    // Add OSM tile and marker layers
    oMarkersLayer = new OpenLayers.Layer.Markers("Markers", {attribution:"<a href='" + sUrl + "' target='_parent'>ScraperWiki</a>"});
    oMap.addLayer(oMarkersLayer);      

    oMap.addLayer(new OpenLayers.Layer.OSM.Mapnik("Osmarender"));

    // saved versions
    //defaulticon = new OpenLayers.Icon('/media/images/mapmarkers/redmarker.png', new OpenLayers.Size(21,25), new OpenLayers.Pixel(-10, -25));
    //defaulticon = new OpenLayers.Icon('http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=o|FF0000|000000', new OpenLayers.Size(21,34), new OpenLayers.Pixel(-10, -34));

    //find where the latlng field is
    var iLatLngIndex = -1;
    var iColourIndex = -1; 
    for (var i=0; i < oData.headings.length; i++) {
        if(oData.headings[i] == 'latlng')
            iLatLngIndex = i;
        if(oData.headings[i] == 'colour')
            iColourIndex = i;
        if(oData.headings[i] == 'chart')
            iChartIndex = i;
    };
    if (iLatLngIndex == -1)
        return; // nothing more to look for

    for (var i=0; i < oData.rows.length; i++) {
        if(oData.rows[i][iLatLngIndex] == "")
            continue;

        //get the lat/lng (maybe it should be organized on the server)
        iLat = oData.rows[i][iLatLngIndex].split(',')[1].replace(')', '');
        iLng = oData.rows[i][iLatLngIndex].split(',')[0].replace('(', '');         
        var oLngLat = new OpenLayers.LonLat(iLat, iLng).transform(new OpenLayers.Projection("EPSG:4326"), oMap.getProjectionObject());         

        //work out the html to pop-up (this could also be a special field)
        var sHtml = ''; 
        var nrows = 0; 
        for (var ii=0; ii < oData.rows[i].length; ii++) {
            sheading = oData.headings[ii]; 
            sdata = oData.rows[i][ii]
            if ((sheading != "chart") && (sheading != "date_scraped") && (sheading != "latlng") && (sheading != "colour") && (sdata != "")) {
                if (sdata.substring(0, 5) == "http:") 
                    sdata = ('<a href="' + sdata + '">' + sdata + '</a>');
                sHtml += ('<tr><td>' + sheading + '</td><td>' + sdata + '</td></tr>');
                nrows++; 
            }
        };
        if (sHtml != '')
            sHtml = '<table>' + sHtml + '</table>';
        else
            sHtml = '<p>blank</p>';

        //make the marker from the chart or the colour (there are issues with it being str(python-object) rather than true json
        var icon = undefined; 
        try {
            if (iChartIndex != -1) {
                chartdata = eval('(' + oData.rows[i][iChartIndex] + ')');
                var oIconSize = new OpenLayers.Size(chartdata['Size'][0], chartdata['Size'][1]);
                var oIconOffset = new OpenLayers.Pixel(chartdata['Pixel'][0], chartdata['Pixel'][1]);
                icon = new OpenLayers.Icon(chartdata['chartimg'], oIconSize, oIconOffset);
            }
        } catch (err) { /*alert(err)*/; }

        if (icon == undefined) {
            colour = "FF0000"; 
            if ((iColourIndex != -1) && oData.rows[i][iColourIndex].match(/[0-9a-fA-F]{6}$/g, colour))
                colour = oData.rows[i][iColourIndex]; 
            var colourimg = 'http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=o|'+colour+'|000000'; 
            icon = new OpenLayers.Icon(colourimg, new OpenLayers.Size(21,34), new OpenLayers.Pixel(-10, -34));
            //icon = defaulticon.clone(); // must have separate object for every point!
        }

        var oMarker = new OpenLayers.Marker(oLngLat, icon)

        oMarkersLayer.addMarker(oMarker);
        oMarker.html = sHtml;
        oMarker.nrows = nrows; 

        oMarker.events.register("mousedown", oMarker,
            function(o, b){
                var oPopup = new OpenLayers.Popup.AnchoredBubble("item", this.lonlat, 
                    new OpenLayers.Size(350,(this.nrows < 3 ? 60 : 250)), this.html, this.icon, true);
                oMap.addPopup(oPopup, true);
            }  );              
    };
     
    //zoom to extent of the markers
    oMap.zoomToExtent(oMarkersLayer.getDataExtent());    
}
