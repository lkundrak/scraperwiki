<?php

class SW_DataStoreClass
{
   private static $m_ds       ;
   protected      $m_socket   ;
   protected      $m_host     ;
   protected      $m_port     ;
   protected $m_scrapername;
   protected $m_runid;

   function __construct ($host, $port, $scrapername, $runid)
   {
      $this->m_socket    = null     ;
      $this->m_host      = $host    ;
      $this->m_port      = $port    ;
      $this->m_scrapername = $scrapername;
      $this->m_runid = $runid;
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
            socket_connect     ($this->m_socket, $this->m_host, $this->m_port) ;
            socket_getsockname ($this->m_socket, $addr, $port) ;
            $getmsg = sprintf  ("GET /?uml=%s&port=%s&vscrapername=%s&vrunid=%s HTTP/1.1\n\n", trim(`/bin/hostname`), $port, urlencode($this->m_scrapername), urlencode($this->m_runid)) ;
            socket_send        ($this->m_socket, $getmsg, strlen($getmsg), MSG_EOR) ;
            socket_recv        ($this->m_socket, $buffer, 0xffff, 0) ;
            $result = json_decode($buffer, true);
            if ($result["status"] != "good")
               throw new Exception ($result["status"]);
      }
   }

   function request($req)
   {
      $this->connect () ;
      $reqmsg  = json_encode ($req) . "\n" ;
      socket_send ($this->m_socket, $reqmsg, strlen($reqmsg), MSG_EOR) ;

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
      socket_send  ($this->m_socket, ".\n", 2, MSG_EOR) ;
      socket_close ($this->m_socket) ;
      $this->m_socket = undef ;
   }

    // function used both to iniatialize the settings and get the object
   static function create ($host = null, $port = null, $scrapername = null, $runid = null)
   {
      if (is_null(self::$m_ds))
         self::$m_ds = new SW_DataStoreClass ($host, $port, $scrapername, $runid);
      return self::$m_ds;
   }
}

?>
