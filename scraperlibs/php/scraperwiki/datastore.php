<?php

class SW_DataStoreClass
{
   private static $m_ds       ;
   protected      $m_socket   ;
   protected      $m_host     ;
   protected      $m_port     ;
   protected $m_scrapername;
   protected $m_runid;
   protected $m_attachables; 
   protected $m_webstore_port;

   function __construct ($host, $port, $scrapername, $runid, $attachables, $webstore_port)
   {
      $this->m_socket    = null     ;
      $this->m_host      = $host    ;
      $this->m_port      = $port    ;
      $this->m_scrapername = $scrapername;
      $this->m_runid = $runid;
      $this->m_attachables = $attachables; 
      $this->m_webstore_port = $webstore_port; 
   }


   function connect ()
   {
      /*
      Connect to the data proxy. The data proxy will need to make an Ident call
      back to get the scraperID. Since the data proxy may be on another machine
      and the peer address it sees will have been subject to NAT or masquerading,
      send the UML name and the socket port number in the request.
      */
      if (is_null($this->m_socket))
      {
            $this->m_socket    = socket_create (AF_INET, SOCK_STREAM, SOL_TCP) ;
            if (socket_connect     ($this->m_socket, $this->m_host, $this->m_port) === FALSE)
                throw new Exception("Could not socket_connect to datastore");
            socket_getsockname ($this->m_socket, $addr, $port) ;
            //print "socket_getsockname " . $addr . ":" . $port . "\n";
            $getmsg = sprintf  ("GET /?uml=%s&port=%s&vscrapername=%s&vrunid=%s HTTP/1.1\n\n", 'lxc', $port, urlencode($this->m_scrapername), urlencode($this->m_runid)) ;
            socket_write        ($this->m_socket, $getmsg);

            socket_recv        ($this->m_socket, $buffer, 0xffff, 0) ;
            $result = json_decode($buffer, true);
            if ($result["status"] != "good")
               throw new Exception ($result["status"]);
      }
   }

   function webstorerequest($req)
   {
        if ($req["maincommand"] == "sqlitecommand")
        {
            if ($req["command"] == "attach")
                return (object)(array('status'=>'ok'));   # done at a higher level
            else if ($req["command"] == "commit")
                return (object)(array('status'=>'ok'));
            else
                return (object)(array("error"=>'Unknown sqlitecommand: '.$req["command"])); 
            return (object)(array("error"=>'Unknown maincommand: '.$req["maincommand"])); 
        }

        $webstoreurl = "http://".$this->m_host.":".$this->m_webstore_port; 
        $username = "resourcedir";  # gets it into the right subdirectory automatically!!!
        $dirscrapername = $this->m_scrapername; 
        if (!$this->m_scrapername)
            $dirscrapername = "DRAFT__".preg_replace("[\.\-]", "_", $this->m_runid); 
        $databaseurl = $webstoreurl."/".$username."/".$dirscrapername; 

        if ($req["maincommand"] == "save_sqlite")
        {
            $table_name = $req["swdatatblname"]; 
            $tableurl = $databaseurl."/".$table_name; 
            $qsl = array(); 
            foreach ($req["unique_keys"] as $key)
                array_push($qsl, "unique=".urlencode($key)); 
            $ldata = $req["data"]; 

            # quick and dirty provision of column types to the webstore
            if (count($ldata) != 0)
            {
                $jargtypes = array(); 
                foreach ($ldata[0] as $k=>$v)
                {
                    if ($v != null)
                    {
                        //if ((count($k) >= 5) && (substr($k, count($k)-5) == "_blob"))
                        //    $vt = "blob";  # coerced into affinity none
                        if (is_int($v))
                            $vt = "integer"; 
                        else if (is_float($v))
                            $vt = "real"; 
                        else
                            $vt = "text"; 
                        $jargtypes[$k] = $vt; 
                    }
                }
                array_push($qsl, "jargtypes=".json_encode($jargtypes)); 
            }
            $target = $tableurl."?".implode("&", $qsl); 

            $curl = curl_init($target);
            $headers = array("Accept: application/json"); 
        }
        else if ($req["maincommand"] == "sqliteexecute")
        {
            $curl = curl_init($databaseurl);
            curl_setopt($curl, CURLOPT_CUSTOMREQUEST, "PUT");
            $headers = array("Accept: application/json+tuples"); 
            $ldata = array("query"=>$req["sqlquery"], "params"=>$req["data"], "attach"=>array()); 
            foreach ($req["attachlist"] as $att)
                array_push($ldata["attach"], array("user"=>$username, "database"=>$att["name"], "alias"=>$att["asname"], "securityhash"=>"somthing")); 
        }

        $headers[] = "Content-Type: application/json"; 
        $headers[] = "X-Scrapername: ".$this->m_scrapername; 
        $headers[] = "X-Runid: ".$this->m_runid; 
        curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($curl, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($curl, CURLOPT_MAXREDIRS, 10);
        curl_setopt($curl, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($curl, CURLOPT_HTTPHEADER, $headers); 
        curl_setopt($curl, CURLOPT_POSTFIELDS, json_encode($ldata)); 
        $res = curl_exec($curl);
        curl_close($curl);
        $jres = json_decode($res); 
        if (property_exists($jres, 'state') && ($jres->state == 'error'))
            return (object)(array("error"=>$jres->message)); 
        if (property_exists($jres, "keys") && property_exists($jres, "data") && (count($jres->data) == 1))
        {
            $ddata = array_combine($jres->keys, $jres->data[0]); 
            if (property_exists((object)($ddata), "state"))  // should be has_key (when I can look it up)
                if ($ddata["state"] == "error")
                    return (object)(array("error"=>$ddata["message"])); 
        }
        return $jres;
   }

   function request($req)
   {
      if ($this->m_webstore_port)
         return $this->webstorerequest($req); 

      $this->connect () ;
      $reqmsg  = json_encode ($req) . "\n" ;
      socket_write ($this->m_socket, $reqmsg);

      $text = '' ;
      while (true)
      {
            socket_recv ($this->m_socket, $buffer, 0xffff, 0) ;
            if (strlen($buffer) == 0)
               break ;
            $text .= $buffer ;
            if ($text[strlen($text)-1] == "\n")
               break ;
      }

      return json_decode($text) ;
   }

   function save ($unique_keys, $scraper_data, $date = null, $latlng = null)
   {
       throw new Exception ("This function is no more and shouldn't be accessible") ;
   }


   function close ()
   {
      socket_write  ($this->m_socket, ".\n");
      socket_close ($this->m_socket) ;
      $this->m_socket = undef ;
   }

    // function used both to iniatialize the settings and get the object
   static function create ($host = null, $port = null, $scrapername = null, $runid = null, $attachables = null, $webstore_port = null)
   {
      if (is_null(self::$m_ds))
         self::$m_ds = new SW_DataStoreClass ($host, $port, $scrapername, $runid, $attachables, $webstore_port);
      return self::$m_ds;
   }
}

?>
