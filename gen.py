from pymclevel import mclevel, nbt
from getmail import *
import random

level = mclevel.fromFile("DungeonBase/level.dat")

#chunkpositions = list(level.allChunks)
#print chunkpositions

start_block = level.getChunk(5,1)
v_tunnel = level.getChunk(1,0)
#basic_room_1 = level.getChunk(2,0)
#basic_room_2 = level.getChunk(3,0)
#pillar_room = level.getChunk(4,0)
#tall_room = level.getChunk(5,0)
stairs = level.getChunk(1,1)
h_tunnel = level.getChunk(2,1)
treasure_room_gaudy = level.getChunk(3,1)
treasure_room_plain = level.getChunk(4,1)
end_room = level.getChunk(6,1)
# Big room is in 6,0; 7,0; and 7,1.

def pickIndex(seed):
	random.seed(seed)
	return random.randint(2,5)

def deleteChunk(chunk):
	chunk.Blocks[:,:,:]=0
	chunk.Data[:,:,:]=0
	chunk.chunkChanged()
	
def replaceChunk(replacee,replacer,h):
	replacee.Blocks[:,:,3+h:] = replacer.Blocks[:,:,3:256-h]
	replacee.Data[:,:,3+h:] = replacer.Data[:,:,3:256-h]
	replacee.chunkChanged()

def deepCopy(replacee,replacer):
	replacee.Blocks[:,:,:] = replacer.Blocks[:,:,:]
	replacee.Data[:,:,:] = replacer.Data[:,:,:]
	replacee.chunkChanged()

def placeFirstRoom(row_num):
	next_room = level.getChunk(0,row_num)
	deepCopy(next_room,start_block)

def placeLastRoom(row_num,h):
	next_room = level.getChunk(0,row_num)
	replaceChunk(next_room,end_room,h)

def placeNextRoom(col_num,row_num,seed,h):
	next_room = level.getChunk(col_num,row_num)
	i = pickIndex(seed)
	roomtype = level.getChunk(i,0)
	replaceChunk(next_room,roomtype,h)
	return next_room

def placeVerTunnel(row_num,h):
	next_room = level.getChunk(0,row_num)
	replaceChunk(next_room,v_tunnel,h)

def placeHorizTunnel(col_num,row_num,h):
	next_room = level.getChunk(col_num,row_num)
	replaceChunk(next_room,h_tunnel,h)

def placeStair(row_num,h):
	next_room = level.getChunk(0,row_num)
	replaceChunk(next_room,stairs,h)

def increaseHeight(row_num,h):
	placeStair(row_num,h)
	return h+8

def makeHole(room,h):
	room.Blocks[15,7:9,4+h:6+h] = 0 # Remove square-shaped hole
	room.Blocks[15,7:9,3+h] = 4     # Replace floor with cobblestone
	room.chunkChanged()

def convertRoom(room,h):
	room.Blocks[0,7:9,4+h:6+h] = 0 # Same as makeHole, but on the left side
	room.Blocks[0,7:9,3+h] = 4     # Ditto.
	room.Blocks[7:9,0,4+h:6+h] = 98  # Fill doorway in with stone bricks
	room.Blocks[7:9,15,4+h:6+h] = 98 # Ditto.
	makeHole(room,h)

def theFloorIsLava(room,h):
	room.Blocks[:,:,2+h:4+h] = 98 # Create retaining area
	room.Blocks[1:15,2:14,3+h] = 10 # Add lava
	room.chunkChanged()

def noFloor(room,h):
	room.Blocks[:,:,:4+h] = 98 # Create walls
	room.Blocks[1:15,2:14,:4+h] = 0 # Remove floor
	room.chunkChanged()

#sets all signs in chunk to text
def setSign(chunkX, chunkY, text=['','','','']):
	print chunkX
	print chunkY
	chunk=level.getChunk(chunkX, chunkY)
	for tileEntity in chunk.TileEntities:
		print tileEntity
		if tileEntity["id"].value == "Sign":
			for i in range(4):
				tileEntity["Text{0}".format(i + 1)].value = text[i]

def main():
	level.createChunk(1,0)
	if num_rooms>6:
		level.createChunk(0,1)
		level.createChunk(1,1)
	current_row_number = 0
	current_col_number = 0
	height = 0
	placeFirstRoom(current_row_number)
	current_row_number += 1
	print 'Fetching mail...'
	maildata = getmail()
	print 'Mail fetched. Building world...'

	for i, thread in enumerate(maildata):
		if i==7:
			break

		if i==4 or i==8:
			height = increaseHeight(current_row_number,height)
		else:
			placeVerTunnel(current_row_number,height)
		#level.saveInPlace()
		#setSign(current_col_number, current_row_number, ['ffff','hh','',''])
		point=[6, 5, 30+32*i]
		tileEntity = level.tileEntityAt(6, 5, 30+32*i)

		linekeys = ["Text" + str(k) for k in range(1, 5)]

		if not tileEntity:
			tileEntity = nbt.TAG_Compound()
			tileEntity["id"] = nbt.TAG_String("Sign")
			tileEntity["x"] = nbt.TAG_Int(point[0])
			tileEntity["y"] = nbt.TAG_Int(point[1])
			tileEntity["z"] = nbt.TAG_Int(point[2])
			for l in linekeys:
				tileEntity[l] = nbt.TAG_String("")

		level.addTileEntity(tileEntity)
		level.getChunk(current_col_number,current_row_number).chunkChanged()

		print thread

		subject ="Untitled"
		fro = ""
		if thread:
			subject = thread[0]['subject'][:15]
			fro = thread[0]['from'][:15]
		setSign(current_col_number,current_row_number, [subject,fro,'',''])
		level.getChunk(current_col_number,current_row_number).chunkChanged()


		current_row_number += 1
		#T-room
		original_col_number=current_col_number
		makeHole(placeNextRoom(current_col_number,current_row_number, random.random(), height), height)
		current_col_number += 1
		#setSign(current_col_number, current_row_number, ['1','2','3','4'])
		for ii, message in enumerate(thread):
			if ii==7:
				break

			placeHorizTunnel(current_col_number,current_row_number,height)
			current_col_number += 1
			convertRoom(placeNextRoom(current_col_number, current_row_number, random.random(), height),height)
			current_col_number += 1
		#TODO add treasure room
		if i%2==1:
			r = level.getChunk(0,current_row_number)
			if height<16:
				theFloorIsLava(r,height)
			else:
				noFloor(r,height)
		current_row_number += 1
		current_col_number=original_col_number
	height = increaseHeight(current_row_number,height)
	current_row_number +=1
	placeLastRoom(current_row_number,height)
	#for i in range(0,5):
		#placeNextRoom(current_col_number,current_row_number,random.random(),height)
		#current_row_number += 1
		#placeVerTunnel(current_row_number,height)
		#current_row_number += 1
	#setSign(2,2, ['1','2','3','4'])
	print 'Built. Saving...'
	level.saveInPlace()
	print 'Done!'

if __name__ == "__main__":
	main()
