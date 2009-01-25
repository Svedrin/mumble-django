import dbus

import datetime
from time import time

# base = ice.stringToProxy( "Meta:tcp -h 127.0.0.1 -p 6502" );
# srv = Murmur.ServerPrx.checkedCast( base );
# met = Murmur.MetaPrx.checkedCast( base );

class mmServer( object ):
	# channels    = dict();
	# players     = dict();
	# id          = int();
	# rootName    = str();
	
	def __init__( self, serverID, serverObj, rootName = '' ):
		if not isinstance( serverObj, dbus.ProxyObject ):
			raise Exception, "mmServer: I need the object returned by dbus.get_object!"
		
		self.dbusObj  = serverObj;
		self.channels = dict();
		self.players  = dict();
		self.id       = serverID;
		self.rootName = rootName;
		
		links         = dict();
		
		for theChan in serverObj.getChannels():
			# Channels - Fields: 0 = ID, 1 = Name, 2 = Parent-ID, 3 = Links
			
			if( theChan[2] == -1 ):
				# No parent
				self.channels[theChan[0]] = mmChannel( theChan );
			else:
				self.channels[theChan[0]] = mmChannel( theChan, self.channels[theChan[2]] );
			
			# process links - if the linked channels are known, link; else save their ids to link later
			for linked in theChan[3]:
				if linked in self.channels:
					self.channels[theChan[0]].linked.append( self.channels[linked] );
				else:
					if linked not in links:
						links[linked] = list();
					links[linked].append( self.channels[theChan[0]] );
					#print "Saving link: %s <- %s" % ( linked, self.channels[theChan[0]] );
			
			# check if earlier round trips saved channel ids to be linked to the current channel
			if theChan[0] in links:
				for targetChan in links[theChan[0]]:
					targetChan.linked.append( self.channels[theChan[0]] );
		
		if self.rootName:
			self.channels[0].name = self.rootName;
		
		for thePlayer in serverObj.getPlayers():
			# Players - Fields: 0 = UserID, 6 = ChannelID
			self.players[ thePlayer[0] ] = mmPlayer( thePlayer, self.channels[ thePlayer[6] ] );
			
	
	playerCount = property(
		lambda self: len( self.players ),
		None
		);
	
	def __str__( self ):
		return '<Server "%s" (%d)>' % ( self.rootName, self.id );
	
	def visit( self, callback, lvl = 0 ):
		if not callable( callback ):
			raise Exception, "a callback should be callable...";
		
		# call callback first on myself, then visit my root chan
		callback( self, lvl );
		self.channels[0].visit( callback, lvl + 1 );


class mmChannel( object ):
	# channels  = list();
	# subchans  = list();
	# id        = int();
	# name      = str();
	# parent    = mmChannel();
	# linked    = list();
	# linkedIDs = list();
	
	def __init__( self, channelObj, parentChan = None ):
		self.players  = list();
		self.subchans = list();
		self.linked   = list();
		
		(self.id, self.name, parent, self.linkedIDs ) = channelObj;
		
		self.parent = parentChan;
		if self.parent is not None:
			self.parent.subchans.append( self );
	
	def parentChannels( self ):
		if self.parent is None or isinstance( self.parent, mmServer ):
			return [];
		return self.parent.parentChannels() + [self.parent.name];
	
	playerCount = property(
		lambda self: len( self.players ) + sum( [ chan.playerCount for chan in self.subchans ] ),
		None
		);
	
	def __str__( self ):
		return '<Channel "%s" (%d)>' % ( self.name, self.id );
	
	def visit( self, callback, lvl = 0 ):
		# call callback on myself, then visit my subchans, then my players
		callback( self, lvl );
		for sc in self.subchans:
			sc.visit( callback, lvl + 1 );
		for pl in self.players:
			pl.visit( callback, lvl + 1 );



class mmPlayer( object ):
	# muted        = bool;
	# deafened     = bool;
	# suppressed   = bool;
	# selfmuted    = bool;
	# selfdeafened = bool;
	
	# channel      = mmChannel();
	# dbaseid      = int();
	# userid       = int();
	# name         = str();
	# onlinesince  = time();
	# bytesPerSec  = int();
	
	def __init__( self, playerObj, playerChan ):
		( self.userid, self.muted, self.deafened, self.suppressed, self.selfmuted, self.selfdeafened, chanID, self.dbaseid, self.name, onlinetime, self.bytesPerSec ) = playerObj;
		self.onlinesince = datetime.datetime.fromtimestamp( float( time() - onlinetime ) );
		self.channel = playerChan;
		self.channel.players.append( self );
	
	def __str__( self ):
		return '<Player "%s" (%d, %d)>' % ( self.name, self.userid, self.dbaseid );
	
	def isAuthed( self ):
		return self.dbaseid != -1;
	
	# kept for compatibility to mmChannel (useful for traversal funcs)
	playerCount = property(
		lambda self: -1,
		None
		);
	
	def visit( self, callback, lvl = 0 ):
		callback( self, lvl );


if __name__ == '__main__':
	# connect to dbus
	bus = dbus.SystemBus();
	
	# get our murmur servers
	dbus_base = 'net.sourceforge.mumble.murmur';
	murmur = bus.get_object( dbus_base, '/' );
	
	# example callback
	def travrz( obj, lvl ):
		print lvl*'-', str(obj);
	
	# show each server
	for srv in murmur.getBootedServers():
		theSrv = bus.get_object( dbus_base, '/%d' % srv );
		
		srvobj = mmServer( srv, theSrv, 'teh %d srvz root' % srv );
		srvobj.visit( travrz );
	
