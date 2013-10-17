#!/bin/python2

from pymclevel import mclevel, nbt
from getmail import *
import random

level = mclevel.fromFile("DungeonBase/level.dat")

# TODO:
# * Move all instances of "level" out of helper functions -- work on room references, instead.
#   * Make saved level independent of base level.
# * Replace makeHole, unmakeHole, and convertRoom to a general-purpose doorway-maker.
# * Add more roomtypes (other than jumping puzzle)
# * Change pillar_room from a map object to a function

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
	return to
	
def replaceChunk(to,fro,h):
	to.Blocks[:,:,3+h:] = fro.Blocks[:,:,3:256-h]
	to.Data[:,:,3+h:] = fro.Data[:,:,3:256-h]
	to.chunkChanged()
	return to

def deepCopy(to,fro):
	to.Blocks[:,:,:] = fro.Blocks[:,:,:]
	to.Data[:,:,:] = fro.Data[:,:,:]
	to.chunkChanged()
	return to

def placeFirstRoom(room):
	deepCopy(room,start_block)
	return room

def placeLastRoom(room,h):
	replaceChunk(room,end_room,h)
	return room

def placeTreasureRoom(room, h):
	replaceChunk(room,treasure_room_plain,h)
	return room

def placeGaudyTreasureRoom(room, h):
	replaceChunk(room,treasure_room_gaudy,h)
	return room

def placeNextRoom(room, seed, h):
	i = pickIndex(seed)
	roomtype = level.getChunk(i,0)
	replaceChunk(room,roomtype,h)
	return room

def placeVerTunnel(roon, h):
	replaceChunk(room,v_tunnel,h)

def placeHorizTunnel(room, h):
	replaceChunk(room, h_tunnel, h)

def placeStair(room, h):
	replaceChunk(room, stairs, h)

def increaseHeight(room, h):
	placeStair(room, h)
	return h+8

def makeHole(room, h):
	room.Blocks[15,7:9,4+h:6+h] = 0 # Remove square-shaped hole
	room.Blocks[15,7:9,3+h] = 4     # Replace floor with cobblestone
	room.chunkChanged()

def unmakeHole(room, h):
	room.Blocks[15,7:9,4+h:6+h] = 98
	room.chunkChanged()

def convertRoom(room, h):
	room.Blocks[0,7:9,4+h:6+h] = 0 # Same as makeHole, but on the left side
	room.Blocks[0,7:9,3+h] = 4     # Ditto.
	room.Blocks[7:9,0,4+h:6+h] = 98  # Fill doorway in with stone bricks
	room.Blocks[7:9,15,4+h:6+h] = 98 # Ditto.
	makeHole(room, h)

def theFloorIsLava(room, h):
	room.Blocks[:,:,2+h:4+h] = 98 # Create retaining area
	room.Blocks[1:15,2:14,3+h] = 10 # Add lava
	room.chunkChanged()

def noFloor(room, h):
	room.Blocks[:,:,:4+h] = 98 # Create walls
	room.Blocks[1:15,2:14,:4+h] = 0 # Remove floor
	room.chunkChanged()

def floorPuzzle(room, h, dangerBlock, diff):
	for i in range(2,14):
		for j in range(1,15):
			k = random.randint(0,diff)
			if k == 0:
				room.Blocks[j,i,3+h] = 1
			else:
				room.Blocks[j,i,3+h] = dangerBlock

#sets all signs in chunk to text
def setSign(room, text=['','','','']):
	for tileEntity in chunk.TileEntities:
		print tileEntity
		#if tileEntity["id"].value == "Sign":
			#for i in range(4):
				#tileEntity["Text{0}".format(i + 1)].value = text[i]
	return room

def main():
	level.createChunk(1,0)
	if num_rooms>6:
		level.createChunk(0,1)
		level.createChunk(1,1)
	current_row_number = 0
	current_col_number = 0
	height = 0

	placeFirstRoom(level.getChunk(current_col_number,current_row_number))
	current_row_number += 1
	
	print 'Fetching mail...'
	maildata = getmail()
	print 'Mail fetched. Building world...'
	#print maildata

	for i, thread in enumerate(maildata):
		if i==10:
			break

		if i==4 or i==8:
			height = increaseHeight(current_row_number,height)
		else:
			placeVerTunnel(current_row_number,height)

		placeVerTunnel(current_row_number,height)
		#level.saveInPlace()
		print current_col_number
		print current_row_number
		r = setSign(level.getChunk(current_col_number,current_row_number))
		point=[6, 5+(int)(i/4)*8, 30+32*i]
		tileEntity = level.tileEntityAt(6, 5+(int)(i/4)*8, 30+32*i)

		linekeys = ["Text" + str(k) for k in range(1, 5)]

		if not tileEntity:
			tileEntity = nbt.TAG_Compound()
			tileEntity["id"] = nbt.TAG_String("Sign")
			tileEntity["x"] = nbt.TAG_Int(point[0])
			tileEntity["y"] = nbt.TAG_Int(point[1])
			tileEntity["z"] = nbt.TAG_Int(point[2])
			for l in linekeys:
				tileEntity[l] = nbt.TAG_String("")

		subject ="Draft"
		fro = ""
		if thread:
			subject = thread[0]['subject'][:15]
			fro = thread[0]['from'][:15]
		tileEntity[linekeys[0]] = subject
		tileEntity[linekeys[1]] = fro

		level.addTileEntity(tileEntity)
		r.chunkChanged()

		if i==4 or i==8:
			height = increaseHeight(current_row_number,height)
		else:
			placeVerTunnel(current_row_number,height)
		#setSign(level.getChunk(2+current_col_number, 2+current_row_number), ['ffff','hh','',''])
		current_row_number += 1
		#T-room
		original_col_number=current_col_number
		if len(fro):
			seed = fro
		else:
			seed = random.random()
		if len(thread)>1: #no openings on single rooms
			makeHole(placeNextRoom(level.getChunk(current_col_number,current_row_number), seed, height), height)
		else:
			placeNextRoom(level.getChunk(current_col_number,current_row_number), seed, height)
		current_col_number += 1
		#setSign(level.getChunk(current_col_number, current_row_number), ['1','2','3','4'])
		for ii, message in enumerate(thread):
			if ii==7:
				break

			placeHorizTunnel(level.getChunk(current_col_number, current_row_number), height)
			current_col_number += 1
			r = convertRoom(placeNextRoom(level.getChunk(current_col_number, current_row_number), seed, height), height)
#			if current_col_number%2==1:
			# level.getChunk(current_col_number,current_row_number)
			if height<16:
				theFloorIsLava(r,height)
				dangerBlock = 10
			else:
				noFloor(r,height)
				dangerBlock = 0
			floorPuzzle(r,height,dangerBlock,(height/8)+1)

			current_col_number += 1
		r = level.getChunk(current_col_number, current_row_number)
		if current_col_number - original_col_number <5:
			unmakeHole(level.getChunk(current_col_number - 1, current_row_number), height)
			#placeNextRoom(current_col_number, current_row_number, seed, height)
		elif current_col_number - original_col_number <8:
			placeTreasureRoom(r, height)
		else:
			placeGaudyTreasureRoom(r, height)

		if i%2==1:
			r = level.getChunk(0,current_row_number)
			if height<16:
				theFloorIsLava(r,height)
				dangerBlock = 10
			else:
				noFloor(r,height)
				dangerBlock = 0
			floorPuzzle(r,height,dangerBlock,(height/8)+1)
		current_row_number += 1
		current_col_number=original_col_number
	height = increaseHeight(current_row_number,height)
	current_row_number +=1
	placeLastRoom(level.getChunk(current_col_number,current_row_number), height)
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
