# 3D Network Toolbox for ArcGIS 10.x and Pro
# Christopher D. Higgins
# Department of Human Geography
# University of Toronto Scarborough
# https://higgicd.github.io

# Jimmy Chan
# Department of Land Surveying and Geo-Informatics
# The Hong Kong Polytechnic University
    
import arcpy, os

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        self.label = "3D Network Toolbox"
        self.alias = "3DNetworkToolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Network2Dto3D]

class Network2Dto3D(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "3D Network Generation from 2D Network and DTM"
        self.description = "Generate 3D Network from 2D Network using Digital Terrain Model. This version is compatible with ArcGIS 10.4 or later and Pro."

        self.canRunInBackground = True
        self.category = "3D Network Generation"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input Surface",
            name="Input_Surface",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Input Network (2D)",
            name="Input_Line_Feature_Class",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="Sample Distance",
            name="Distance",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")

        param2.filter.type = "Range"
        param2.filter.list = [1.0,  float("inf")]
        param2.defaultEnvironmentName = 10.0
        param2.value = 10.0

        param3 = arcpy.Parameter(
            displayName="Network has No Split edges",
            name="FalseSplit",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        param3.value = False
        
        param4 = arcpy.Parameter(
            displayName="Network has No Slope edges",
            name="FalseSlope",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        param4.value = False

        param5 = arcpy.Parameter(
            displayName="Output Network (3D)",
            name="Network_3D",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Output")

        params = [param0, param1, param2, param3, param4, param5]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        try:
            if arcpy.CheckExtension("3D") != "Available" or arcpy.CheckExtension("Spatial") != "Available":
                raise Exception
        except Exception:
                return False  # tool cannot be executed

        return True  # tool can be executed

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):

        arcpy.CheckOutExtension("3D")
        arcpy.CheckOutExtension("Spatial")
        
        input_surface = parameters[0].valueAsText
        input_lines = parameters[1].valueAsText
        sample_dist = parameters[2].value
        flag_nosplit = parameters[3].value
        flag_noslope = parameters[4].value
        output_lines = parameters[5].valueAsText
        search_radius = 0.001
        
        def split_lines(input_fc, sample_dist, search_radius):
            arcpy.AddMessage("Generating sample points...")
            points = arcpy.GeneratePointsAlongLines_management(input_fc, r"in_memory\points", "DISTANCE", sample_dist, "", "")
            
            arcpy.AddMessage("Splitting lines at points...")
            lines_split = arcpy.SplitLineAtPoint_management(input_fc, points, r"in_memory\lines_split", search_radius)
            
            return lines_split
        
        def calculate_z(input_fc):
            MaximumValueFunc = "def MaximumValue(*args): return max(args)"
            
            arcpy.AddField_management(input_fc, "Start_Z", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.AddField_management(input_fc, "End_Z", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.AddField_management(input_fc, "Max_Z", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            
            arcpy.CalculateField_management(input_fc, "Start_Z", "!SHAPE!.firstpoint.Z", "PYTHON_9.3", "")
            arcpy.CalculateField_management(input_fc, "End_Z", "!SHAPE!.lastpoint.Z", "PYTHON_9.3", "")
            arcpy.CalculateField_management(input_fc, "Max_Z", "MaximumValue(!Start_Z!, !End_Z!)", "PYTHON_9.3", MaximumValueFunc)
        
        def tobler_calc(input_fc):
            arcpy.AddMessage("Calculating walk times...")
            
            # Add Z Information
            arcpy.AddZInformation_3d(input_fc, "LENGTH_3D;AVG_SLOPE", "NO_FILTER")
            
            # Add walk time fields
            arcpy.AddField_management(input_fc, "FT_MIN_2D", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.AddField_management(input_fc, "TF_MIN_2D", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.AddField_management(input_fc, "FT_MIN_3D", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.AddField_management(input_fc, "TF_MIN_3D", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

            # Calculate walk time fields
            arcpy.CalculateField_management(input_fc, "FT_MIN_2D", "(!shape.length!/(5036.742125))*60", "PYTHON", "")
            arcpy.CalculateField_management(input_fc, "TF_MIN_2D", "(!shape.length!/(5036.742125))*60", "PYTHON", "")
            arcpy.CalculateField_management(input_fc, "FT_MIN_3D", "(!Length3D!/((6*(math.exp((-3.5)*(math.fabs((!End_Z!-!Start_Z!)/(!shape.length!)+0.05)))))*1000))*60", "PYTHON", "")
            arcpy.CalculateField_management(input_fc, "TF_MIN_3D", "(!Length3D!/((6*(math.exp((-3.5)*(math.fabs((!Start_Z!-!End_Z!)/(!shape.length!)+0.05)))))*1000))*60", "PYTHON", "")
        
        # step 1 - interpolate shape
        lines_interpolate = arcpy.InterpolateShape_3d(input_surface, input_lines, 
                                                      r"in_memory\lines_interpolate", "", "1", 
                                                      "BILINEAR", "DENSIFY", "0")
        
        # main
        if flag_nosplit == True:
            # Process: Select Layer By Attribute
            lines_interpolate_lyr = arcpy.MakeFeatureLayer_management(lines_interpolate, "lines_interpolate_lyr")
            arcpy.SelectLayerByAttribute_management(lines_interpolate_lyr, "NEW_SELECTION", "NO_SPLIT = 1")
            lines_nosplit = arcpy.CopyFeatures_management(lines_interpolate_lyr, r"in_memory\lines_nosplit")
            
            # process no_split lines
            calculate_z(lines_nosplit)
            lines_nosplit_3D = arcpy.FeatureTo3DByAttribute_3d(lines_nosplit, r"in_memory\lines_nosplit_3D", "Start_Z", "End_Z")
            arcpy.AddMessage("Finished processing No Split lines...")
            
            # process lines to be split
            arcpy.SelectLayerByAttribute_management(lines_interpolate_lyr, "SWITCH_SELECTION", "")
            lines_2D = arcpy.CopyFeatures_management(lines_interpolate_lyr, r"in_memory\lines_2D")
            lines_3D = split_lines(lines_2D, sample_dist, search_radius)
            calculate_z(lines_3D)
            
            # append two datasets
            arcpy.Append_management(lines_nosplit_3D, lines_3D, "TEST", "", "")
            tobler_calc(lines_3D)
        
        else:
            lines_2D = arcpy.MakeFeatureLayer_management(lines_interpolate, "lines_2D")
            lines_3D = split_lines(lines_2D, sample_dist, search_radius)
            calculate_z(lines_3D)            
            tobler_calc(lines_3D)
        
        # Replace 3D walk time with 2D walk time for any No_Slope lines
        if flag_noslope == True:
            lines_3D_lyr = arcpy.MakeFeatureLayer_management(lines_3D, "lines_3D_lyr")
            arcpy.SelectLayerByAttribute_management(lines_3D_lyr, "NEW_SELECTION", "NO_SLOPE = 1")
            arcpy.CalculateField_management(lines_3D_lyr, "FT_MIN_3D", "!FT_MIN_2D!", "PYTHON", "")
            arcpy.CalculateField_management(lines_3D_lyr, "TF_MIN_3D", "!TF_MIN_2D!", "PYTHON", "")
        
        # export output
        arcpy.CopyFeatures_management(lines_3D, output_lines)

        # Delete in-memory table
        arcpy.Delete_management(r"in_memory\lines_3D")
        arcpy.Delete_management(r"in_memory\points")
        arcpy.Delete_management(r"in_memory\lines_interpolate")
        if flag_nosplit == True:
            arcpy.Delete_management(r"in_memory\lines_2D")
            arcpy.Delete_management(r"in_memory\lines_nosplit_3D")

        arcpy.CheckInExtension("3D")
        arcpy.CheckInExtension("Spatial")

        return