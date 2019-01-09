# 3D Network Toolbox for ArcGIS 10.x
    # Christopher D. Higgins
    # Jimmy Chan
    # Department of Land Surveying and Geo-Informatics
    # The Hong Kong Polytechnic University
    
import arcpy, os

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        self.label = "3D Network Toolbox"
        self.alias = "Network3D"

        # List of tool classes associated with this toolbox
        self.tools = [Network2DTo3D]

class Network2DTo3D(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "3D Network Generation from 2D Network and DTM"
        self.description = "Generate 3D Network from 2D Network using Digital Terrain Model. This version is compatible on ArcGIS 10.4 or later."

        self.canRunInBackground = True
        self.category = "3D Network Generation"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input Surface",
            name="Input_Surface",
            datatype=["DERasterDataset", "GPFeatureLayer"],
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
            name="Network_3D__3_",
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

        lines = "in_memory\\lines"
        points = "in_memory\\points"
        lines_interpolate = "in_memory\\lines_interpolate"
        lines_nosplit = "in_memory\\lines_nosplit"
        nosplit_to3d = "in_memory\\nosplit_to3d"
        Search_Radius = 0.001
        lines_interpolate_lyr = "in_memory\\lines_interpolate_lyr"
        lines_nosplit_lyr = "in_memory\\lines_nosplit_lyr"
        output_feature_class_lyr = "in_memory\\output_feature_class_lyr"
        startEndMaxZ = [["Start_Z", "!SHAPE!.firstpoint.Z"], ["End_Z", "!SHAPE!.lastpoint.Z"], ["Max_Z", "MaximumValue(!Start_Z!, !End_Z!)"]]
        MaximumValueFunc = "def MaximumValue(*args): return max(args)"
        output_feature_class = "in_memory\\ordinary_output"

        # Process: Interpolate Shape
        arcpy.InterpolateShape_3d(parameters[0].valueAsText, parameters[1].valueAsText, lines_interpolate, "", "1", "BILINEAR", "DENSIFY", "0")
        # Process: Add Fields
        arcpy.AddField_management(lines_interpolate, "Start_Z", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.AddField_management(lines_interpolate, "End_Z", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.AddField_management(lines_interpolate, "Max_Z", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
               
        # See if there are No_Split edges specified
        if parameters[3].value == True:
            # Process: Select Layer By Attribute
            arcpy.MakeFeatureLayer_management(lines_interpolate, lines_interpolate_lyr)
            arcpy.SelectLayerByAttribute_management(lines_interpolate_lyr, "NEW_SELECTION", "NO_SPLIT = 1")
            
            # Process: Copy out the No Split edges to the lines_nosplit feature
            arcpy.CopyFeatures_management(lines_interpolate_lyr, lines_nosplit)
            
            # Process: Switch back to the edges that are NOT to be split
            arcpy.SelectLayerByAttribute_management(lines_interpolate_lyr, "SWITCH_SELECTION", "")
            arcpy.CopyFeatures_management(lines_interpolate_lyr, lines)

            # Process No_Split edges
            for eachZ in startEndMaxZ:
                if eachZ[0] != "Max_Z":
                    # Process: Calculate Field (1), (2)
                    arcpy.CalculateField_management(lines_nosplit, eachZ[0], eachZ[1], "PYTHON_9.3", "")
                else:
                    # Process: Calculate Field (3)
                    arcpy.CalculateField_management(lines_nosplit, eachZ[0], eachZ[1], "PYTHON_9.3", MaximumValueFunc)
            
            # Feature To 3D By Attribute for No_Split edges
            arcpy.FeatureTo3DByAttribute_3d(lines_nosplit, nosplit_to3d, "Start_Z", "End_Z")
            
            arcpy.AddMessage("Finished processing No Split lines...")
            
            # Generate Points Along Lines
            if parameters[2].valueAsText == None:
                arcpy.GeneratePointsAlongLines_management(lines, points, "DISTANCE", 10, "", "")
            elif not parameters[2].valueAsText.isnumeric():
                arcpy.GeneratePointsAlongLines_management(lines, points, "DISTANCE", 10, "", "")
            else:
                arcpy.GeneratePointsAlongLines_management(lines, points, "DISTANCE", float(parameters[2].valueAsText), "", "")
            
            arcpy.AddMessage("Finished generating points...")
            
            # Split Lines at Points
            arcpy.SplitLineAtPoint_management(lines, points, output_feature_class, Search_Radius)
            for eachZ in startEndMaxZ:
                if eachZ[0] != "Max_Z":
                    # Process: Calculate Field (6), (7)
                    arcpy.CalculateField_management(output_feature_class, eachZ[0], eachZ[1], "PYTHON_9.3", "")
                else:
                    # Process: Calculate Field (8)
                    arcpy.CalculateField_management(output_feature_class, eachZ[0], eachZ[1], "PYTHON_9.3", MaximumValueFunc)
            
            arcpy.AddMessage("Finished splitting lines at points...")

            # Append split and no_split lines
            arcpy.Append_management(nosplit_to3d, output_feature_class, "TEST", "", "")

            # Add Z Information
            arcpy.AddZInformation_3d(output_feature_class, "LENGTH_3D;AVG_SLOPE", "NO_FILTER")

            # Add walk time fields
            arcpy.AddField_management(output_feature_class, "FT_MIN_2D", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.AddField_management(output_feature_class, "TF_MIN_2D", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.AddField_management(output_feature_class, "FT_MIN_3D", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.AddField_management(output_feature_class, "TF_MIN_3D", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

            # Calculate walk time fields
            arcpy.CalculateField_management(output_feature_class, "FT_MIN_2D", "(!shape.length!/(5036.742125))*60", "PYTHON", "")
            arcpy.CalculateField_management(output_feature_class, "TF_MIN_2D", "(!shape.length!/(5036.742125))*60", "PYTHON", "")
            arcpy.CalculateField_management(output_feature_class, "FT_MIN_3D", "(!Length3D!/((6*(math.exp((-3.5)*(math.fabs((!End_Z!-!Start_Z!)/(!shape.length!)+0.05)))))*1000))*60", "PYTHON", "")
            arcpy.CalculateField_management(output_feature_class, "TF_MIN_3D", "(!Length3D!/((6*(math.exp((-3.5)*(math.fabs((!Start_Z!-!End_Z!)/(!shape.length!)+0.05)))))*1000))*60", "PYTHON", "")
            
            # Replace 3D walk time with 2D walk time for any No_Slope lines
            if parameters[4].value == True:
                arcpy.MakeFeatureLayer_management(output_feature_class, output_feature_class_lyr)
                arcpy.SelectLayerByAttribute_management(output_feature_class_lyr, "NEW_SELECTION", "NO_SLOPE = 1")
                arcpy.CalculateField_management(output_feature_class_lyr, "FT_MIN_3D", "!FT_MIN_2D!", "PYTHON", "")
                arcpy.CalculateField_management(output_feature_class_lyr, "TF_MIN_3D", "!TF_MIN_2D!", "PYTHON", "")
            
            arcpy.AddMessage("Finished calculating walk times...")
        
        # Alternate workflow if no No_Split parameter is set
        else:
            # Generate Points Along Lines
            if parameters[2].valueAsText == None:
                arcpy.GeneratePointsAlongLines_management(lines_interpolate, points, "DISTANCE", 10, "", "")
            elif not parameters[2].valueAsText.isnumeric():
                arcpy.GeneratePointsAlongLines_management(lines_interpolate, points, "DISTANCE", 10, "", "")
            else:
                arcpy.GeneratePointsAlongLines_management(lines_interpolate, points, "DISTANCE", float(parameters[2].valueAsText), "", "")

            # Generate Points Along Lines
            if parameters[2].valueAsText == None:
                arcpy.GeneratePointsAlongLines_management(lines, points, "DISTANCE", 10, "", "")
            elif not parameters[2].valueAsText.isnumeric():
                arcpy.GeneratePointsAlongLines_management(lines, points, "DISTANCE", 10, "", "")
            else:
                arcpy.GeneratePointsAlongLines_management(lines, points, "DISTANCE", float(parameters[2].valueAsText), "", "")
            
            arcpy.AddMessage("Finished generating points...")
                        
            # Split Lines at Points
            arcpy.SplitLineAtPoint_management(lines_interpolate, points, output_feature_class, Search_Radius)
            for eachZ in startEndMaxZ:
                if eachZ[0] != "Max_Z":
                    # Process: Calculate Field (6), (7)
                    arcpy.CalculateField_management(output_feature_class, eachZ[0], eachZ[1], "PYTHON_9.3", "")
                else:
                    # Process: Calculate Field (8)
                    arcpy.CalculateField_management(output_feature_class, eachZ[0], eachZ[1], "PYTHON_9.3", MaximumValueFunc)
            
            arcpy.AddMessage("Finished splitting lines at points...")

            # Add Z Information
            arcpy.AddZInformation_3d(output_feature_class, "LENGTH_3D;AVG_SLOPE", "NO_FILTER")

            # Add walk time fields
            arcpy.AddField_management(output_feature_class, "FT_MIN_2D", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.AddField_management(output_feature_class, "TF_MIN_2D", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.AddField_management(output_feature_class, "FT_MIN_3D", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.AddField_management(output_feature_class, "TF_MIN_3D", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

            # Calculate walk time fields
            arcpy.CalculateField_management(output_feature_class, "FT_MIN_2D", "(!shape.length!/(5036.742125))*60", "PYTHON", "")
            arcpy.CalculateField_management(output_feature_class, "TF_MIN_2D", "(!shape.length!/(5036.742125))*60", "PYTHON", "")
            arcpy.CalculateField_management(output_feature_class, "FT_MIN_3D", "(!Length3D!/((6*(math.exp((-3.5)*(math.fabs((!End_Z!-!Start_Z!)/(!shape.length!)+0.05)))))*1000))*60", "PYTHON", "")
            arcpy.CalculateField_management(output_feature_class, "TF_MIN_3D", "(!Length3D!/((6*(math.exp((-3.5)*(math.fabs((!Start_Z!-!End_Z!)/(!shape.length!)+0.05)))))*1000))*60", "PYTHON", "")
            
            # Replace 3D walk time with 2D walk time for any No_Slope lines
            if parameters[4].value == True:
                arcpy.MakeFeatureLayer_management(output_feature_class, output_feature_class_lyr)
                arcpy.SelectLayerByAttribute_management(output_feature_class_lyr, "NEW_SELECTION", "NO_SLOPE = 1")
                arcpy.CalculateField_management(output_feature_class_lyr, "FT_MIN_3D", "!FT_MIN_2D!", "PYTHON", "")
                arcpy.CalculateField_management(output_feature_class_lyr, "TF_MIN_3D", "!TF_MIN_2D!", "PYTHON", "")
            
            arcpy.AddMessage("Finished calculating walk times...")

        # Prepare output
        arcpy.CopyFeatures_management(output_feature_class, parameters[5].valueAsText)

        # Delete in-memory table
        arcpy.Delete_management("in_memory\\lines_interpolate")
        arcpy.Delete_management("in_memory\\lines_nosplit")
        arcpy.Delete_management("in_memory\\nosplit_to3d")
        arcpy.Delete_management("in_memory\\lines_interpolate_lyr")
        arcpy.Delete_management("in_memory\\lines_nosplit_lyr")
        arcpy.Delete_management("in_memory\\lines")
        arcpy.Delete_management("in_memory\\points")
        arcpy.Delete_management("in_memory\\ordinary_output")

        arcpy.CheckInExtension("3D")
        arcpy.CheckInExtension("Spatial")

        return

