# -*- coding: utf-8 -*-

import arcpy
import xml.etree.ElementTree as ET

removedFieldTypes = ["Geometry", "GlobalID", "OID"]

def msg(txt):
    print(txt)
    arcpy.AddMessage(txt)
    arcpy.SetProgressorLabel(txt)

def AddMD(fc, template):
    # get existing metadata from fc and template
    fc_md = arcpy.metadata.Metadata(fc)
    template_md = arcpy.metadata.Metadata(template)

    # extract template field metadata
    template_xml = template_md.xml
    # arcpy.AddMessage("template_xml: " + str(template_xml))
    start_tag = '<attr xmlns="">'
    end_tag = '</detailed>'
    # arcpy.AddMessage("template_1: " + str(template_xml.split(start_tag, 1)))
    # arcpy.AddMessage("template_0: " + str(template_xml.split(start_tag, 1)[1].split(end_tag)))
    try: template_txt = template_xml.split(start_tag, 1)[1].split(end_tag)[0]
    except:
        msg(' --- ERROR --- ')
        msg(' metadata has likely not been synced ')
        msg(' open the featureclass metadata, and in the metadata tab click the sync button')
        msg(' then try running this tool again')
        raise SystemExit
    # arcpy.AddMessage("template_txt: " + str(template_txt))

    # insert template txt into original metadata
    fc_xml = fc_md.xml
    fc_xml_list = fc_xml.split(end_tag)

    new_xml = start_tag.join([fc_xml_list[0], template_txt])
    new_xml = end_tag.join([new_xml, fc_xml_list[1]])

    # save xml
    fc_md.xml = new_xml

    fc_md.save()
    # best_md = arcpy.metadata.Metadata(fc)
    # best_md.copy(fc_md)
    # best_md.save()
    return

def PrintXML(xml, depth = 0):
    for child in xml:
        string = str(child.tag)+":"+str(child.attrib)
        if child.attrib != "PictureX":
            string += " " + str(child.text)
        msg("\t"*depth+string)
        if len(list(child)) > 0:
            PrintXML(child, depth+1)   

def EditFieldMDName(fc, oldName, newName, newAlias):
    fc_md = arcpy.metadata.Metadata(fc)
    tree = ET.fromstring(fc_md.xml)
    fieldMetadataList = tree.find("eainfo").find("detailed").findall("attr") #Get the list of fields
    if fieldMetadataList:
        fldList = []
        for attr in fieldMetadataList:
            # fldList.append(attr.findtext("attrlabl"))
            if attr.findtext("attrlabl") == oldName:
                if newName:
                    attr.find("attrlabl").text = newName
                if newAlias:
                    attr.find("attalias").text = newAlias
        msg(fldList)
    else:
        msg('Error with how the program finds field metadata, fix the EditFieldMetaDataName function')
        raise SystemExit
    
    fc_md.xml = ET.tostring(tree)

    fc_md.save()

def DeleteFieldsFromMD(fc, nameList):
    if type(nameList) == list and len(nameList) > 0:
        msg("Deleting Fields from metadata: "+str(nameList))
        upperNameList = [name.upper() for name in nameList]
        fc_md = arcpy.metadata.Metadata(fc)

        tree = ET.fromstring(fc_md.xml)

        fieldMetaDataRoot = tree.find("eainfo").find("detailed")
        fieldMetadataList = fieldMetaDataRoot.findall("attr") #Get the list of fields
        if fieldMetadataList:
            fldList = []
            for attr in fieldMetadataList:
                if attr.findtext("attrlabl").upper() in upperNameList:
                    msg("Deleting old metadata for: "+str(attr.findtext("attrlabl")))
                    fieldMetaDataRoot.remove(attr)
            msg(fldList)
        else:
            msg('Error with how the program finds field metadata, fix the DeleteFieldsFromMetaData function')
            raise SystemExit
        msg([field.findtext("attrlabl") for field in tree.find("eainfo").find("detailed").findall("attr")])
        msg([field.findtext("attrlabl") for field in fieldMetaDataRoot.findall("attr")])
        fc_md.xml = ET.tostring(tree)

        fc_md.save()
    else:
        msg("Error, not a valid list of fields to delete from metadata")
        raise SystemExit

def DeleteFieldFromMD(fc, name):
    DeleteFieldsFromMD(fc, [name])

def FixFieldMDCapitalization(fc):
    fc_md = arcpy.metadata.Metadata(fc)
    fields = [field.name for field in arcpy.ListFields(fc)]
    upperFields = [field.upper() for field in fields]

    tree = ET.fromstring(fc_md.xml)
    fieldMetadataList = tree.find("eainfo").find("detailed").findall("attr") #Get the list of fields
    if fieldMetadataList:
        for attr in fieldMetadataList:
            name = attr.findtext("attrlabl")
            if name.upper() in upperFields:
                if name not in fields:
                    attr.find("attrlabl").text = fields[upperFields.index(name.upper())]
    else:
        msg('Error with how the program finds field metadata, fix the FixFieldMetaDataNameCapitalization function')
        raise SystemExit
    
    fc_md.xml = ET.tostring(tree)

    fc_md.save()

def FixFieldMDOrder(fc):
    fc_md = arcpy.metadata.Metadata(fc)

    tree = ET.fromstring(fc_md.xml)
    treeBackup = tree.copy()
    try:
        fieldMetaDataRoot = tree.find("eainfo").find("detailed")
        fieldMetadataList = fieldMetaDataRoot.findall("attr") #Get the list of fields

        for attr in fieldMetadataList:
            fieldMetaDataRoot.remove(attr)

        fieldMDNames = [field.findtext("attrlabl").upper() for field in fieldMetadataList]

        fieldOrder = [f.name.upper() for f in arcpy.ListFields(fc)]
        for field in fieldOrder:
            if field in fieldMDNames:
                index = fieldMDNames.index(field)
                fieldMetaDataRoot.append(fieldMetadataList[index])

                del fieldMetadataList[index]
                del fieldMDNames[index]
            else:
                msg("Error: " + str(field) + " does not have corresponding metadata")
        if fieldMDNames:
            fieldMetaDataRoot.extend(fieldMetadataList)
            msg(str(fieldMDNames) + " were added to the end as they were not found within  the fields list.")
        # msg(fieldMetaDataRoot.findall("attr"))
        # msg([field.findtext("attrlabl") for field in tree.find("eainfo").find("detailed").findall("attr")])
        # msg([field.findtext("attrlabl") for field in fieldMetaDataRoot.findall("attr")])    
        fc_md.xml = ET.tostring(tree)
    except:
        arcpy.AddWarning("Could not fix order of fields within metadata")
        fc_md.xml = ET.tostring(treeBackup)
    fc_md.save()

def CheckFieldMDQuality(fc): 
    fc_md = arcpy.metadata.Metadata(fc)
    fields = [field.name for field in arcpy.ListFields(fc)]
    upperFields = [field.upper() for field in fields]
    # msg(fields)
    # msg(upperFields)
    unusedFields = upperFields.copy() #Check for missing fields in metadata
    usedFields = [] #Check for duplicate filds in metadata

    tree = ET.fromstring(fc_md.xml)
    fieldMetadataList = tree.find("eainfo").find("detailed").findall("attr") #Get the list of fields
    if fieldMetadataList:
        for attr in fieldMetadataList:
            name = attr.findtext("attrlabl")
            uName = name.upper()
            msg(name)
            if uName in usedFields:
                msg("\t"+str(name) + "is a duplicate field within the metadata")
            else:
                if uName in upperFields:
                    if name not in fields:
                        msg("\t"+str(name) +" should be " + str(fields[upperFields.index(uName)]))
                    unusedFields.remove(uName)
                    usedFields.append(uName)
                else:
                    msg("\t"+str(name) +" is not in the list of fields, possibly should be deleted")
        if unusedFields:
            msg("The following fields do not have metadata: "+ str(unusedFields))
    else:
        msg('Error with how the program finds field metadata, fix the FixFieldMetaDataNameCapitalization function')
        raise SystemExit
    
    fc_md.xml = ET.tostring(tree)

    fc_md.save()

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Add Data Standards + Metadata"
        self.alias = "Add Data Standards + Metadata"

        # List of tool classes associated with this toolbox
        self.tools = [AddDataStandardsToExistingFC, JustAddMetadata, CheckFieldMetadataQuality]#, FixFieldMetadataOrder]

class AddDataStandardsToExistingFC(object):
    def __init__(self):
        """This tool adds data standard fields to an existing feature class."""
        self.label = "Add Data Standard Fields to Existing Feature Class"
        self.description = "This tool adds data standard fields to an existing feature class."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        fc = arcpy.Parameter(
                displayName = "Destination Feature Class",
                name = "fc",
                datatype = "GPTableView",
                parameterType = "Required",
                direction = "Input")

        template = arcpy.Parameter(
                displayName = "Template Feature Class",
                name = "template",
                datatype = "DEFeatureClass",
                parameterType = "Required",
                direction = "Input")

        createBackup = arcpy.Parameter(
                displayName = "Create Backup of the Feature Class?",
                name = "Create_Backup",
                datatype = "Boolean",
                parameterType = "Optional",
                direction = "Input")

        default_unit_code = arcpy.Parameter(
                displayName = "Default Unit Code (Optional)",
                name = "default_unit_code",
                datatype = "GPString",
                parameterType = "Optional",
                direction = "Input")

        default_unit_name = arcpy.Parameter(
                displayName = "Default Unit Name (Optional)",
                name = "default_unit_name",
                datatype = "GPString",
                parameterType = "Optional",
                direction = "Input")

        default_group_code = arcpy.Parameter(
                displayName = "Default Group Code (Optional)",
                name = "default_group_code",
                datatype = "GPString",
                parameterType = "Optional",
                direction = "Input")

        default_group_name = arcpy.Parameter(
                displayName = "Default Group Name (Optional)",
                name = "default_group_name",
                datatype = "GPString",
                parameterType = "Optional",
                direction = "Input")

        default_region_code = arcpy.Parameter(
                displayName = "Default Region Code (Optional)",
                name = "default_region_name",
                datatype = "GPString",
                parameterType = "Optional",
                direction = "Input")
        default_region_code.value = "PWR"

        fieldInfo = arcpy.Parameter(
                displayName = "Existing Fields - (By default existing field will be altered to match standards while preserving existing data)",
                name = "Existing_Fields",
                datatype = "GPString",
                parameterType = "Optional",
                direction = "Input",
                multiValue=True
        )
        fieldInfo.columns = [["GPString", "Existing Field Name", "READONLY"], ["GPBoolean", "Rename Existing Field and Create Non-Populated Field from Template?"], ["GPString", "Replacement Field Name"], ["GPString", "Replacement Field Alias"]]
        fieldInfo.enabled = False
        
        params = [fc, template, createBackup, default_unit_code, default_unit_name, default_group_code, default_group_name, default_region_code, fieldInfo, arcpy.Parameter(
                displayName = "Test String",
                name = "String",
                datatype = "GPString",
                parameterType = "Optional",
                direction = "Input")]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        EmptyFieldParam = ["", False, "", ""]

        if parameters[0].valueAsText and parameters[1].valueAsText:
            oldFieldNames = arcpy.ListFields(parameters[0].valueAsText)
            newFieldNames = arcpy.ListFields(parameters[1].valueAsText)
            existingInputs = []
            if parameters[8].value:
                existingInputs = [row[1:] for row in parameters[8].value]
            while(len(existingInputs) > 0 and existingInputs[-1] == EmptyFieldParam[1:]):
                existingInputs.pop()
            # compare fields, find similar
            oldFieldNamesUpper = [f.name.upper() for f in oldFieldNames if f.type not in removedFieldTypes] 
            newFieldNamesUpper = [f.name.upper() for f in newFieldNames if f.type not in removedFieldTypes]
            MatchFieldNames = list(set(oldFieldNamesUpper).intersection(set(newFieldNamesUpper)))
            paramListLeng = max(len(MatchFieldNames), len(existingInputs))
            if paramListLeng > 0:
                Fields = [(MatchFieldNames[i] if len(MatchFieldNames) > i else "") for i in range(paramListLeng)]
                inputs = [(existingInputs[i] if len(existingInputs) > i else EmptyFieldParam[1:]) for i in range(paramListLeng)]
                ParamValues = [[Fields[i]]+inputs[i] for i in range(paramListLeng)]
                parameters[8].value = (ParamValues)
                parameters[8].enabled = True
            else:
                parameters[8].value = [EmptyFieldParam]
                parameters[8].enabled = False
            # parameters[-1].value = str([field.name for field in ])
            pass
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        # parameters[-1].setWarningMessage(len(arcpy.ListFields(parameters[1].valueAsText)))
        if parameters[8].value and parameters[8].enabled:
            if parameters[8].value[-1][0] == "":
                parameters[8].setWarningMessage("Warning: too many Values in this parameter. Extraneous inputs will be ignored")
            if parameters[0].valueAsText and parameters[1].valueAsText:
                oldFields = arcpy.ListFields(parameters[0].valueAsText)
                oldFieldNamesUpper = [field.name.upper() for field in oldFields]
                newFields = arcpy.ListFields(parameters[1].valueAsText)
                newFieldNamesUpper = [field.name.upper() for field in newFields]

                ErrorMessage = ""
                WarningMessage = ""
                for row in parameters[8].value:
                    oldField = oldFields[oldFieldNamesUpper.index(row[0].upper())]
                    newField = newFields[newFieldNamesUpper.index(row[0].upper())]
                    if oldField.type != newField.type:
                        if row[1] == False:
                            ErrorMessage += (str(row[0])+" does not match type ("+str(oldField.type)+" -> " +str(newField.type) + ")\n")
                    if newField.length:
                        if oldField.length:
                            if oldField.length > newField.length:
                                WarningMessage += (str(row[0])+" length will be shortening, may cause issues: ("+str(oldField.length)+" -> " +str(newField.length) + ")\n")
                        else:
                            WarningMessage += (str(row[0])+" length will be shortening, may cause issues: ("+str(oldField.length)+" -> " +str(newField.length) + ")\n")
                if ErrorMessage:
                    parameters[8].setErrorMessage(ErrorMessage)
                elif WarningMessage:
                    parameters[8].setWarningMessage(WarningMessage)
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        fcBase = parameters[0].valueAsText
        fc = arcpy.da.Describe(fcBase)['catalogPath']
        msg(fc)
        # return
        template = parameters[1].valueAsText
        create_backup = parameters[2].value
        unit_code = parameters[3].valueAsText
        unit_name = parameters[4].valueAsText
        group_code = parameters[5].valueAsText
        group_name = parameters[6].valueAsText
        region_code = parameters[7].valueAsText
        field_renamings = parameters[8].value

        # get the gdb where the fc lives
        gdb = '\\'.join(fc.split('\\')[0:-1])

        fc_name = fc.split("\\")[-1]

        if create_backup:
            msg('... Making backup copy of original feature class ...')
            backup_fc_name = f"{fc_name}_original"
            
            # let user know backup copy already exists
            if arcpy.Exists(f"{gdb}\{backup_fc_name}"):
                msg(f" -- {backup_fc_name} already exists in {gdb} --")
                msg(" -- not creating a backup --")

            # create backup
            else:
                datatype = arcpy.da.Describe(fc)["dataElementType"]
                if datatype == "DETable": arcpy.conversion.TableToTable(fc, gdb, backup_fc_name)
                elif datatype == "DEFeatureClass": arcpy.conversion.FeatureClassToFeatureClass(fc, gdb, backup_fc_name)
                else:
                    msg("Cannont create copy, file is of type " + str(datatype))
                    raise SystemExit

        if field_renamings:
            msg(f'... Rename data standard fields that already exist in {fc_name} ...')

            # compare fields, find similar
            FCfield_names = [f.name.upper() for f in arcpy.ListFields(fc)] 
            FCRealfield_names = [f.name for f in arcpy.ListFields(fc)] #Is this needed?
            STfield_names = [f.name.upper() for f in arcpy.ListFields(template)]
            # MatchField_Names = list(set(FCfield_names).intersection(set(STfield_names)))
            matchedFields = [row[0] for row in field_renamings if row[0] != ""]
            msg('... Renaming existing fields...')
            delFields = []
            for row in field_renamings:
                field = row[0]
                msg(row)
                if field:
                    realFld = FCRealfield_names[FCfield_names.index(field)]
                    if row[1]:
                        if row[2] or row[3]:
                            newName = arcpy.ValidateFieldName(row[2], gdb)
                            newAlias = row[3]
                            if not row[3]:
                                newAlias = row[2]
                            if not row[2]:
                                newName = row[3]
                            msg("{0}->{1} {2}".format(realFld, newName, newAlias))
                            
                            try: 
                                arcpy.management.AlterField(fc, realFld, newName, newAlias)
                                EditFieldMDName(fc, realFld, newName, newAlias)
                            except Exception as e:
                                msg(str(e))
                                msg("Name cannot be set to "+str(newName)+". Ending Program")
                                raise SystemExit
                        else:
                            arcpy.AddError("No new name given for renamed fields")
                            raise SystemExit
            fc_md = arcpy.metadata.Metadata(fc)
            fc_md.synchronize()

        existingFields = [row[0] for row in field_renamings if not row[1]]
        fcFields = arcpy.ListFields(fc)
        tempFieldsUpper = [f.name.upper() for f in arcpy.ListFields(template)]

        existingFields.extend([f.name.upper() for f in fcFields if f.type in removedFieldTypes and f.name.upper() in tempFieldsUpper]) #Override metadata for removed field types
        if len(existingFields) > 0:
            DeleteFieldsFromMD(fc, existingFields)

        
        # get domains in template gdb
        template_gdb = '\\'.join(template.split('\\')[0:-1])
        template_doms = {dom.name: dom for dom in arcpy.da.ListDomains(template_gdb)}

        # adding fields!
        msg('... Adding data standards ...')

        # domains already in fc gdb
        doms = [dom.name for dom in arcpy.da.ListDomains(gdb)]

        for fld in arcpy.ListFields(template):

            # don't add objectid or shape fields
            if fld.type in removedFieldTypes: continue

            msg(f' - {fld.name}')

            # handle domains
            if fld.domain != '':

                # if domain has not been added to gdb yet
                if fld.domain not in doms:
                    dom = template_doms[fld.domain]

                    # parse domain inputs
                    domType = 'CODED' if dom.domainType == 'CodedValue' else 'Range'

                    # if dom.splitPolicy == 'DefaultValue': domSP = 'DEFAULT'
                    # elif dom.splitPolicy == 'Duplicate': domSP = 'DUPLICATE'
                    # else: domSP = 'GEOMETRY'
                    domSP = 'DUPLICATE'

                    if dom.mergePolicy == 'AreaWeighted': domMP = 'AREA_WEIGHTED'
                    elif dom.mergePolicy == 'SumValues': domMP = 'SUM_VALUES'
                    else: domMP = "DEFAULT"

                    arcpy.management.CreateDomain(gdb,
                                                  dom.name,
                                                  dom.description,
                                                  dom.type,
                                                  domType,
                                                  domSP,
                                                  domMP)
                    doms.append(fld.domain)
                    msg(f'   - {dom.name} added to gdb')

                    # add coded values
                    if dom.domainType == 'CodedValue':
                        for cv in dom.codedValues:
                            arcpy.management.AddCodedValueToDomain(gdb,
                                                                   dom.name,
                                                                   cv,
                                                                   dom.codedValues[cv])
                        msg(f'   - coded values added to {dom.name}')
            if fld.name.upper() not in existingFields:
                # create the field
                arcpy.management.AddField(fc,
                                        fld.name,
                                        fld.type,
                                        fld.precision,
                                        fld.scale,
                                        fld.length,
                                        fld.aliasName,
                                        '',
                                        '',
                                        fld.domain)
            else:
                realFld = FCRealfield_names[FCfield_names.index(fld.name.upper())]
                try: 
                    fieldTypesList ={"Integer":"LONG", "String":"TEXT", "SmallInteger": "SHORT"}
                    fType = fld.type
                    if fType in fieldTypesList: fType = fieldTypesList[fType]
                    arcpy.management.AlterField(fc, realFld, fld.name, fld.aliasName, field_length=fld.length)
                except Exception as e:
                    msg("{4} {5}".format(fc, realFld, fld.name, fld.aliasName, fType, fld.length))
                    msg("error: "+str(e))
                    msg("Name cannot be set to "+str(fld.name))
                if fld.domain:
                    try: 
                        arcpy.management.AssignDomainToField(fc, realFld, fld.domain)
                    except:
                        msg("Domain cannot be set to "+str(fld.domain))
                        

            # add defaults if desired
            if unit_code and fld.name == "UNITCODE":
                arcpy.management.AssignDefaultToField(fc, "UNITCODE", unit_code)
            if unit_name and fld.name == "UNITNAME":
                arcpy.management.AssignDefaultToField(fc, "UNITNAME", unit_name)
            if group_code and fld.name == "GROUPCODE":
                arcpy.management.AssignDefaultToField(fc, "GROUPCODE", group_code)
            if group_name and fld.name == "GROUPNAME":
                arcpy.management.AssignDefaultToField(fc, "GROUPNAME", group_name)
            if region_code and fld.name == "REGIONCODE":
                arcpy.management.AssignDefaultToField(fc, "REGIONCODE", region_code)

        msg('... Adding field metadata ...')

        AddMD(fc, template)

        msg('... Fixing field metadata formatting...')
        FixFieldMDCapitalization(fc)
        FixFieldMDOrder(fc)

        msg('... Tool complete ...')
        
        return

class JustAddMetadata(object):
    def __init__(self):
        """This tool adds metadata for the data standards to the data standard metadata."""
        self.label = "Add JUST the Field Metadata"
        self.description = "This tool adds metadata to a feature class that already has Data Standard Fields but does not yet have the metadata to describe those fields."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        fc = arcpy.Parameter(
                displayName = "Destination Feature Class",
                name = "fc",
                datatype = "GPTableView",
                parameterType = "Required",
                direction = "Input")

        fc.value = r'C:\Users\DShreve\Downloads\test_20230314_1_1.gdb\YOSE_Sign_Inventory'

        template = arcpy.Parameter(
                displayName = "Source Feature Class",
                name = "template",
                datatype = "DEFeatureClass",
                parameterType = "Required",
                direction = "Input")

        template.value = r'\\inpyosegis\Yosemite_EGIS\Templates\Geodatabase_Templates\NPS_CORE_20160810\NPS_CORE_20160810.gdb\CORE_EXTENDED_pt'
        
        params = [fc, template]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

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
        """The source code of the tool."""
        
        fcBase = parameters[0].valueAsText
        fc = arcpy.da.Describe(fcBase)['catalogPath']
        template = parameters[1].valueAsText
        gdb = '\\'.join(fc.split('\\')[0:-1])

        msg('... Adding field metadata ...')

        AddMD(fc, template)

        msg('... Fixing field metadata formatting...')
        FixFieldMDCapitalization(fc)
        FixFieldMDOrder(fc)

        msg('... Tool complete ...')
        
        return

class CheckFieldMetadataQuality(object):

    def __init__(self):
        self.label = "Check Field Metadata Quality"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        params = [arcpy.Parameter(
            displayName = "Feature Class",
            name = "Feature Class",
            datatype = "GPTableView",
            parameterType = "Required",
            direction = "Input")
        ]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        fcBase = parameters[0].valueAsText
        fc = arcpy.da.Describe(fcBase)['catalogPath']
        CheckFieldMDQuality(fc)
        return