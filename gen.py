#!/bin/python2

from pymclevel import mclevel, nbt
from getmail import *
import random
import os
import shutil

# TODO:
# * Move all instances of "level" out of helper functions -- work on room references, instead.
# * Replace makeHole, unmakeHole, and convertRoom to a general-purpose doorway-maker.
# * Add more roomtypes (other than jumping puzzle)
# * Change pillar_room from a map object to a function

rooms = {
		"start"    : [5,1],
		"v_tunnel" : [1,0],
		"basic"    : [2,0],
		"basic2"   : [3,0],
		"pillar"   : [4,0],
		"tall"     : [5,0],
		"stairs"   : [1,1],
		"h_tunnel" : [2,1],
		"treasure" : [4,1],
		"gaudy"    : [3,1],
		"end"      : [6,1]
		}
# Big room is in 6,0; 7,0; and 7,1.

def deleteChunk(chunk):
	chunk.Blocks[:,:,:]=0
	chunk.Data[:,:,:]=0
	chunk.chunkChanged()
	return chunk
	
def roomCopy(fro,to,h):
	to.Blocks[:,:,3+h:] = fro.Blocks[:,:,3:256-h]
	to.Data[:,:,3+h:] = fro.Data[:,:,3:256-h]
	to.chunkChanged()
	return to

def deepCopy(fro,to):
	to.Blocks[:,:,:] = fro.Blocks[:,:,:]
	to.Data[:,:,:] = fro.Data[:,:,:]
	to.chunkChanged()
	return to

def roomType(room_name, world):
	room_loc = rooms[room_name]
	return world.getChunk(room_loc[0],room_loc[1])

def placeNextRoom(room, seed, h, roomArray):
	random.seed(seed)
	i = random.randint(0,len(roomArray)-1)
	roomCopy(roomArray[i], room, h)
	return room

def makeHole(room, h):
	room.Blocks[15,7:9,4+h:6+h] = 0 # Remove square-shaped hole
	room.Blocks[15,7:9,3+h] = 4     # Replace floor with cobblestone
	room.chunkChanged()
	return room

def unmakeHole(room, h):
	room.Blocks[15,7:9,4+h:6+h] = 98
	room.chunkChanged()
	return room

def setExits(room, h, left, right, top, bottom):
	if left:
		l_block = 0
	else:
		l_block = 98
	if right:
		r_block = 0
	else:
		r_block = 98
	if top:
		t_block = 0
	else:
		t_block = 98
	if bottom:
		b_block = 0
	else:
		b_block = 98
	floor_mat = 4
	floor = 3+h

	# Set doorways
	room.Blocks[0,7:9,floor+1:floor+3]  = l_block
	room.Blocks[15,7:9,floor+1:floor+3] = r_block
	room.Blocks[7:9,0,floor+1:floor+3]  = t_block
	room.Blocks[7:9,15,floor+1:floor+3] = b_block

	# Set floors
	room.Blocks[0,7:9,floor]  = floor_mat
	room.Blocks[15,7:9,floor] = floor_mat
	room.Blocks[7:9,0,floor]  = floor_mat
	room.Blocks[7:9,15,floor] = floor_mat
	room.chunkChanged()
	return room

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
	for tileEntity in room.TileEntities:
		print tileEntity
		#if tileEntity["id"].value == "Sign":
			#for i in range(4):
				#tileEntity["Text{0}".format(i + 1)].value = text[i]
	return room

def main():
	shutil.copytree("DungeonBase","Dungeon")
	baseLevel = mclevel.fromFile(os.path.join("DungeonBase","level.dat"))

	## This clears the base map of anything but template chunks
	#chunkPositions = list(baseLevel.allChunks)
	#for x,z in chunkPositions:
	#	if z==0 or z==1:
	#		if x>0 and x<8:
	#			continue
	#	deleteChunk(baseLevel.getChunk(x,z))
	#
	#baseLevel.saveInPlace()
	
	start_block = roomType("start", baseLevel)
	v_tunnel = roomType("v_tunnel", baseLevel)
	h_tunnel = roomType("h_tunnel", baseLevel)
	stairs = roomType("stairs", baseLevel)
	basic_room_1 = roomType("basic", baseLevel)
	basic_room_2 = roomType("basic2", baseLevel)
	pillar_room = roomType("pillar", baseLevel)
	tall_room = roomType("tall", baseLevel)
	treasure_room_gaudy = roomType("gaudy", baseLevel)
	treasure_room_plain = roomType("treasure", baseLevel)
	end_room = roomType("end", baseLevel)

	room_sel = [basic_room_1, basic_room_2, pillar_room, tall_room]

	level = mclevel.fromFile(os.path.join("Dungeon","level.dat"))
	
	current_row_number = 0
	current_col_number = 0
	height = 0
	
	deepCopy(start_block,level.getChunk(current_col_number,current_row_number))
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

		roomCopy(v_tunnel, level.getChunk(0,current_row_number), height)
		#level.saveInPlace()
		#print current_col_number
		#print current_row_number
		#r = setSign(level.getChunk(current_col_number,current_row_number))
		r = level.getChunk(current_col_number,current_row_number)
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
			roomCopy(stairs,level.getChunk(0, current_row_number), height)
			height += 8
		else:
			roomCopy(v_tunnel, level.getChunk(0,current_row_number), height)
		#setSign(level.getChunk(2+current_col_number, 2+current_row_number), ['ffff','hh','',''])
		current_row_number += 1
		#T-room
		original_col_number=current_col_number
		if len(fro):
			seed = fro
		else:
			seed = random.random()
		if len(thread)>1: #no openings on single rooms
			makeHole(placeNextRoom(level.getChunk(current_col_number,current_row_number), seed, height, room_sel), height)
		else:
			placeNextRoom(level.getChunk(current_col_number,current_row_number), seed, height, room_sel)
		current_col_number += 1
		#setSign(level.getChunk(current_col_number, current_row_number), ['1','2','3','4'])
		for ii, message in enumerate(thread):
			if ii==7:
				break

			roomCopy(h_tunnel, level.getChunk(current_col_number,current_row_number), height)
			current_col_number += 1
			r = setExits(placeNextRoom(level.getChunk(current_col_number, current_row_number), seed, height, room_sel), height, True, True, False, False)
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
		elif current_col_number - original_col_number <8:
			roomCopy(treasure_room_plain, r, height)
		else:
			roomCopy(treasure_room_gaudy, r, height)
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
	roomCopy(stairs,level.getChunk(0,current_row_number), height)
	height += 8
	current_row_number +=1
	roomCopy(end_room, level.getChunk(current_col_number, current_row_number), height)

	print 'Built. Saving...'
	level.saveInPlace()
	print 'Done!'

if __name__ == "__main__":
	main()
