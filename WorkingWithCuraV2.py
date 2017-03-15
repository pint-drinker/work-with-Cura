#Communicates with Cura and sends an STL file to it. Cura slices the file and spits out a gcode file.
#This gcode file is then parsed and features are pulled out about the build.

#IMPORT NECESSARY TOOLBOXES
import os
import math
import timeit
import time
#import easygui

#DEFINE FOLDER PATH NAMES
path_to_CuraEngine = "/Applications/Cura.app/Contents/MacOS/CuraEngine"
stl_folder = "/users/dwensberg/Documents/CodingWork/PaperLessParts/stlFiles/"
gcode_folder = "/users/dwensberg/Documents/CodingWork/PaperLessParts/GcodeFiles/"
output_folder = "/users/dwensberg/Documents/CodingWork/PaperLessParts/AnalysisFiles/"

#MACHINE PARAMETER AND EXTRUDER FOLDERS
json_machine_path = "/Applications/Cura.app/Contents/Resources/resources/definitions/"
json_extruder_path = "/Applications/Cura.app/Contents/Resources/resources/extruders/"

#SELECTING MACHINE (turn this into UI)
#ultimaker 3 files
machine = json_machine_path + "ultimaker3.def.json"
extruder = json_extruder_path + "ultimaker3_extruder_left.def.json"
prefix = "ULT3_"

#makerbot replicator files
##machine = json_machine_path + "makerbotreplicator.def.json"
##extruder = json_extruder_path + "ord_extruder_0.def.json"
##prefix = "MAKERBOT_"

#kossel pro files
##machine = json_machine_path + "kossel_pro.def.json"
##extruder = json_extruder_path + "ord_extruder_0.def.json"
##prefix = "KOSSEL_"

START=time.time()

#CLASS DEFINITIONS
class BuildInfo:
    given_time = 0
    time_total = 0
    z_init = 0
    build_height = 0
    num_lay = 0
    slice_thickness = 0
    distance_total = 0
    time_g0 = 0
    distance_g0 = 0
    speed_g0 = 0
    time_g1 = 0
    distance_g1 = 0
    speed_g1 = 0
    extrusion_total = 0 
    count_wall_outer = 0
    time_wall_outer = 0
    ext_wall_outer = 0
    count_wall_inner = 0
    time_wall_inner = 0
    ext_wall_inner = 0
    count_fill = 0
    time_fill = 0
    ext_fill = 0
    count_skirt = 0
    time_skirt = 0
    ext_skirt = 0
    layer_start = []
    layer_end = []
    
    def __init__(self, name):
        self.name = name
        
    def add_travel_info(self, dx, dext, dt, speed_setting, type_setting):
        self.time_total = self.time_total + dt
        self.distance_total = self.distance_total + dx
        self.extrusion_total = self.extrusion_total + dext
        if speed_setting == "G0":
            self.time_g0 = self.time_g0 + dt
            self.distance_g0 = self.distance_g0 + dx
        elif speed_setting == "G1":
            self.time_g1 = self.time_g1 + dt
            self.distance_g1 = self.distance_g1 + dx
        if type_setting == "SKIRT":
            self.time_skirt = self.time_skirt + dt
            self.ext_skirt = self.ext_skirt + dext
        elif type_setting == "WALL-OUTER":
            self.time_wall_outer = self.time_wall_outer + dt
            self.ext_wall_outer = self.ext_wall_outer + dext
        elif type_setting == "WALL-INNER":
            self.time_wall_inner == self.time_wall_inner + dt
            self.ext_wall_inner = self.ext_wall_inner + dext
        elif type_setting == "FILL":
            self.time_fill = self.time_fill + dt
            self.ext_fill = self.ext_fill + dext

    def add_count(self, type_setting):
        if type_setting == "SKIRT":
            self.count_skirt = self.count_skirt + 1
        elif type_setting == "WALL-OUTER":
            self.count_wall_outer = self.count_wall_outer + 1
        elif type_setting == "WALL-INNER":
            self.count_wall_inner = self.count_wall_inner + 1
        elif type_setting == "FILL":
            self.count_fill = self.count_fill + 1

    def add_layer_points(self, line_num, pt_type):
        if pt_type == "start":
            self.layer_start.append(line_num)
        else:
            self.layer_end.append(line_num)
        
            
#FUNCTION DEFINITIONS
def run_Cura(filename,gcode_folder):
    names = os.listdir(gcode_folder)
    val = 0
    for name in names:
        if filename.find(name) > -1:
            val = 1
            break
    return val

def distance(p1,p2):
    return math.sqrt((p1[0]-p2[0])**2+(p1[1]-p2[1])**2)

def line_look(line):
    #output is going to be a list with first entry as description
    out = [];
    if (line.find("M")>-1):
        out.append("M")
    elif (line.find(";TYPE:")>-1):
        out.append("TYPE")
        temp = line.split(':',1)
        st = temp[1].find("\n")
        str1 = ""
        i = 0
        for i,char in enumerate(temp[1]):
            if i<st:
                str1 = str1 + char
            i = i + 1
        out.append(str1)
    elif (line.find("G")>-1):
        if line.find("G1")>-1:
            out.append("G1")
        else:
            out.append("G0")
        temp = line.split()
        ln = len(temp)
        for piece in temp:
            if piece.find("F")>-1:
                out.append("F")
                out.append(float(piece[1:len(piece)]))
            elif piece.find('X')>-1:
                out.append("X")
                out.append(float(piece[1:len(piece)]))
            elif piece.find("Y")>-1:
                out.append("Y")
                out.append(float(piece[1:len(piece)]))
            elif piece.find("E")>-1:
                out.append("E")
                out.append(float(piece[1:len(piece)]))
            elif piece.find("Z")>-1:
                out.append("Z")
                out.append(float(piece[1:len(piece)]))
    else:
        out.append("&&")
    return out

def fnum(num):
    return "{0:.3f}".format(num)

def make_report(info, filename):
    fn=open(filename,"w")
    fn.write("Build Report Generated by CuraAnalysisV2 \n")
    fn.write("Report on filename: " + filename+"\n")
    fn.write(" \n")
    fn.write("Total Metrics: \n")
    fn.write("Total time (hr): " + fnum(info.given_time/3600) + "\n")
    fn.write("Build Height (mm): " + fnum(info.build_height - info.z_init) + "\n")
    fn.write("Number of layers: " + fnum(info.num_lay) + "\n")
    fn.write("Slice thickness (mm): " + fnum((info.build_height - info.z_init)/(info.num_lay)) + "\n")
    fn.write("Total Time spent traveling (hr): " + fnum(info.time_total/3600) + "\n")
    fn.write("Total head distance travelled (mm): " + fnum(info.distance_total) + "\n")
    fn.write("Total time spent in rapid motion G0 (hr): " + fnum(info.time_g0/3600) + "\n")
    fn.write("Total distance in rapid motion G0 (mm): " + fnum(info.distance_g0) + "\n")
    fn.write("Average fast head speed G0 (mm/min): " + fnum(info.speed_g0) + "\n")
    fn.write("Total time spent extruding G1 (hr): " + fnum(info.time_g1/3600) + "\n")
    fn.write("Total distance G1 (mm): " + fnum(info.distance_g1) + "\n")
    fn.write("Average extrusion speed G1 (mm/min): " + fnum(info.speed_g1) + "\n")
    fn.write("Total extruded length (mm): " + fnum(info.extrusion_total) + "\n")
    fn.write("\n")
    fn.write("FEATURE STATISTICS: \n")
    fn.write("Total outer wall count: " + fnum(info.count_wall_outer) + "\n")
    fn.write("Total outer wall time (hr): "+ fnum(info.time_wall_outer/3600) + "\n")
    fn.write("Total filament used on outer walls (mm): " + fnum(info.ext_wall_outer) + "\n")
    fn.write("Total inner wall count: " + fnum(info.count_wall_inner) + "\n")
    fn.write("Total inner wall time (hr): " + fnum(info.time_wall_inner/3600) + "\n")
    fn.write("Total filament used on inner walls (mm): " + fnum(info.ext_wall_inner) + "\n")
    fn.write("Total fill count: " + fnum(info.count_fill) + "\n")
    fn.write("Total fill time (hr): " + fnum(info.time_fill/3600) + "\n")
    fn.write("Total filament used on fills (mm): " + fnum(info.ext_fill) + "\n")
    fn.write("Total skirt count: " + fnum(info.count_skirt) + "\n")
    fn.write("Total skirt time (hr): " + fnum(info.time_skirt/3600) + "\n")
    fn.write("Total filament used on skirts (mm): " + fnum(info.ext_skirt) + "\n")
    fn.close()
    return

def analyze(name,path_to_CuraEngine,stl_folder,gcode_folder,output_folder,machine,prefix,extruder):
    stl = stl_folder + name + ".stl"
    gcode = gcode_folder + prefix + name + ".txt"
    analysis = output_folder + prefix + name + "_ANALYSIS.txt"

    #See if cura has already run on this file, if not, analyze it
    if run_Cura(gcode,gcode_folder) == 0:
        print("Cura run on "+name+" not found, running through cura")
        #splice together os command and execute
        cmd = path_to_CuraEngine+" slice -j "+machine+" -j "+extruder+" -l "+stl+" -o "+gcode
        #print(cmd)
        os.system(cmd)
    else:
        print("Cura run found on "+name+", skipped cura run, continuing with analysis...")

    gcodeFile = open(gcode,"r")
    
    lnct = 0;
    layerct = 0;
    parse_for_movement = 0
    info = BuildInfo(stl)

    #PREDEFINE VARIABLES
    xo = 0
    yo = 0
    eo = 0
    xn = 0
    yn = 0
    en = 0
    atype = "none"
    aspeed = "none"
    current_speed = 0
    zinit = 100000;
    
    #SCAN THROUGH FILE AND EXTRACT INFORMATION
    for line in gcodeFile:
        lnct = lnct+1;
        #get layer count
        if "LAYER_COUNT" in line:
            temp = line.split(':',1)
            layer_count = int(temp[1])
            info.num_lay = layer_count
            if layer_count > 0:
                parse_for_movement = 1
            else:
                fn = open(analysis,"w")
                fn.write("Build Report Generated by CuraAnalysisV2 \n")
                fn.write("Report on filename: "+name+".stl \n")
                fn.write(" \n")
                print("CURA COULD NOT GENERATE MEANINGFUL GCODE WITH CURRENT SETTINGS")
                fn.write("CURA COULD NOT GENERATE MEANINGFUL GCODE WITH CURRENT SETTINGS \n")
                fn.write("DOUBLE CHECK FOR MEANIFUL STL AND/OR ADJUST MACHINE SETTINGS \n")
                fn.close()
                return
                
        #track start and stop locations of each layer
        if ";LAYER:" in line:
            #signifies beggining of layer
            temp=line.split(':',1)
            layerct = int(temp[1])
            info.add_layer_points(lnct, "start")
            parse_for_movement = 1
        
        #track given layer times
        if ";TIME_ELAPSED:" in line:
            #signifies end of layer
            temp=line.split(':',1)
            info.add_layer_points(lnct, "end")
            info.given_time=float(temp[1])
            parse_for_movement = 0

        #track actions of each line
        if parse_for_movement == 1:
            line_info = line_look(line)
            if line_info[0].find("TYPE") > -1:
                atype = line_info[1]
                info.add_count(atype)
            elif line_info[0].find("G") >- 1:
                if "G1" in line_info:
                    aspeed = "G1"
                elif "G0" in line_info:
                    aspeed = "G0"
                if "X" in line_info:
                    ind = line_info.index("X") + 1
                    xn = line_info[ind]
                if "Y" in line_info:
                    ind = line_info.index("Y") + 1
                    yn = line_info[ind]
                if "Z" in line_info:
                    ind = line_info.index("Z") + 1
                    z = line_info[ind]
                    info.build_height = z
                    if z < zinit:
                        zinit = z
                        info.z_init = zinit
                if "F" in line_info:
                    ind = line_info.index("F") + 1
                    current_speed = line_info[ind]
                if "E" in line_info:
                    ind = line_info.index("E") + 1
                    en = line_info[ind]
                    
                #make calculations
                dis = distance([xn,yn],[xo,yo])
                ext = en - eo
    ##            if ext<0:
    ##                print(en)
    ##                print(eo)
    ##                To reverse the extruder by a given amount (for example to reduce its internal
    ##                pressure while it does an in-air movement so that it doesn't dribble) simply
    ##                use G0 or G1 to send an E value that is less than the currently extruded length.
                if current_speed == 0:
                    time = 0
                else:
                    #need to multiply by 60 because its mm/min
                    time = dis/current_speed*60
                
                #add to active totals
                #geometry type
                info.add_travel_info(dis, ext, time, aspeed, atype)

                #end of calculations for this loop, redefine old to new
                xo = xn
                yo = yn
                eo = en       

    gcodeFile.close()

    #define speed info
    info.speed_g0 = info.distance_g0/info.time_g0*60
    info.speed_g1 = info.distance_g1/info.time_g1*60
    
    #make the report file
    make_report(info, analysis)


#MAIN MAIN MAIN MAIN MAIN MAIN MAIN MAIN MAIN MAIN MAIN MAIN MAIN MAIN

#get stl name and set output names (file select)
names = os.listdir(stl_folder)
namesA = os.listdir(output_folder)
for name in names:
    if name.find(".stl")>-1 or name.find("STL")>-1:
        temp = name.split('.',1)
        fname = temp[0]
        if prefix + fname + "_ANALYSIS.txt" in namesA:
            print("Analysis on " + fname + " found, skipping analysis")
        else:
            print("Analysis on " + fname + " not found, running analysis")
            analyze(fname, path_to_CuraEngine, stl_folder, gcode_folder, output_folder, machine, prefix, extruder)
            
END=time.time()
print("Total Time: " + fnum(END - START) + " seconds")
