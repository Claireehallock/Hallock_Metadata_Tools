# -*- coding: utf-8 -*-

import arcpy
import xml.etree.ElementTree as ET

removedFieldTypes = ["Geometry", "GlobalID", "OID"]

def msg(txt):
    print(txt)
    arcpy.AddMessage(txt)
    arcpy.SetProgressorLabel(txt)

def warn(txt):
    arcpy.AddWarning(txt)

def error(txt):
    arcpy.AddError(txt)

def getWorkspace(layer):
    #Get the Catalog Path
    catalogPath = arcpy.da.Describe(layer)["catalogPath"]
    #Get the folder containing the currecnt file
    workspace = ("\\").join(catalogPath.split("\\")[:-1])
    if not workspace:
        workspace = ("/").join(catalogPath.split("/")[:-1])

    #If contained in an sde, get the sde
    if ".sde/" in catalogPath:
        workspace = catalogPath[:catalogPath.index(".sde/")+4]
    elif ".sde\\" in catalogPath:
        workspace = catalogPath[:catalogPath.index(".sde\\")+4]
    elif catalogPath.endswith(".sde"):
        workspace = catalogPath
    return workspace

def AddMD(fc, template):
    """Copy Metadata Fields to 'fc' from 'template'"""
    # get existing metadata from fc and template
    fc_md = arcpy.metadata.Metadata(fc)
    template_md = arcpy.metadata.Metadata(template)

    # extract template field metadata
    template_xml = template_md.xml

    try: 
        templateAttrs = ET.fromstring(template_xml).find("eainfo").find("detailed").findall("attr")
    except:
        warn(' --- ERROR --- ')
        warn(' metadata has likely not been synced ')
        warn(' open the featureclass metadata, and in the metadata tab click the sync button')
        warn(' then try running this tool again')
        raise SystemExit

    # insert template txt into original metadata
    fc_xml = fc_md.xml
    fc_tree = ET.fromstring(fc_xml)
    fc_tree.find("eainfo").find("detailed").extend(templateAttrs)

    new_xml = ET.tostring(fc_tree)

    # save xml
    fc_md.xml = new_xml
    fc_md.save()
    return

def PrintXML(xml, depth = 0):
    """recursive function to view XML Trees. Depth of 0 means the root of the tree"""
    for child in xml:
        string = str(child.tag)+":"+str(child.attrib)
        if child.attrib != "PictureX":
            string += " " + str(child.text)
        msg("\t"*depth+string)
        if len(list(child)) > 0:
            PrintXML(child, depth+1)   

def EditFieldMDName(fc, oldName, newName, newAlias):
    """Change the name of a field within the metadata (should be used with altering a field name). fc = Feature Class/Table, oldName changes to newName, alias changes to newAlias"""
    fc_md = arcpy.metadata.Metadata(fc)
    tree = ET.fromstring(fc_md.xml)
    fieldMetadataList = tree.find("eainfo").find("detailed").findall("attr") #Get the list of fields
    if fieldMetadataList:
        fldList = []
        for attr in fieldMetadataList:
            if attr.findtext("attrlabl") == oldName: #Find the existing value
                if newName:
                    attr.find("attrlabl").text = newName #rename the field
                if newAlias:
                    attr.find("attalias").text = newAlias #Rename the alias
        msg(fldList)
    else:
        msg('Error with how the program finds field metadata, fix the EditFieldMDName function')
        raise SystemExit
    
    #Convert the tree back to XML and save
    fc_md.xml = ET.tostring(tree)
    fc_md.save()

def DeleteFieldsFromMD(fc, nameList):
    """Delete the fields in 'nameList' from the metadata in 'fc'"""
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
            msg('Error with how the program finds field metadata, fix the DeleteFieldsFromMD function')
            raise SystemExit
        msg([field.findtext("attrlabl") for field in tree.find("eainfo").find("detailed").findall("attr")])
        msg([field.findtext("attrlabl") for field in fieldMetaDataRoot.findall("attr")])
        #Convert the tree back to XML and save
        fc_md.xml = ET.tostring(tree)
        fc_md.save()
    else:
        msg("Error, not a valid list of fields to delete from metadata")
        raise SystemExit

def DeleteFieldFromMD(fc, name):
    """Delete the field in 'name' from the metadata in 'fc'"""
    DeleteFieldsFromMD(fc, [name])

def FixFieldMDCapitalization(fc):
    """Change the capitalization of the Metadata Field names in 'fc' to match the actual field names."""
    fc_md = arcpy.metadata.Metadata(fc)
    fields = [field.name for field in arcpy.ListFields(fc)]
    upperFields = [field.upper() for field in fields]

    tree = ET.fromstring(fc_md.xml)
    fieldMetadataList = tree.find("eainfo").find("detailed").findall("attr") #Get the list of fields
    if fieldMetadataList:
        for attr in fieldMetadataList:
            name = attr.findtext("attrlabl")
            if name.upper() in upperFields: #Find the correct capitalization
                if name not in fields:
                    attr.find("attrlabl").text = fields[upperFields.index(name.upper())] #Set the value ot the correct capitalization
    else:
        msg('Error with how the program finds field metadata, fix the FixFieldMetaDataNameCapitalization function')
        raise SystemExit
    #Convert the tree back to XML and save
    fc_md.xml = ET.tostring(tree)
    fc_md.save()

def FixFieldMDOrder(fc):
    """Reorder the metadata fields in 'fc' to match the order of the fields in 'fc' itself"""
    fc_md = arcpy.metadata.Metadata(fc)

    tree = ET.fromstring(fc_md.xml)
    treeBackup = ET.tostring(tree) #Save a backup of the fields in case something goes wrong while editing them

    try:
        fieldMetaDataRoot = tree.find("eainfo").find("detailed")
        fieldMetadataList = fieldMetaDataRoot.findall("attr") #Get the list of fields

        #Remove the fields from the metadata so they can be re-added in the correct order
        for attr in fieldMetadataList:
            fieldMetaDataRoot.remove(attr)

        #List of field names from the metadata
        fieldMDNames = [field.findtext("attrlabl").upper() for field in fieldMetadataList]

        #List of field names from the feature class/table
        fieldOrder = [f.name.upper() for f in arcpy.ListFields(fc)]
        for field in fieldOrder:
            if field in fieldMDNames:
                #Find the corresponding name from the metadata and add that value
                index = fieldMDNames.index(field)
                fieldMetaDataRoot.append(fieldMetadataList[index])

                del fieldMetadataList[index]
                del fieldMDNames[index]
            else:
                msg("Error: " + str(field) + " does not have corresponding metadata")
        if fieldMDNames: #If not all fields were added via parsing through 'fieldOrder', add them to the end of the list
            fieldMetaDataRoot.extend(fieldMetadataList)
            msg(str(fieldMDNames) + " were added to the end as they were not found within the fields list.") 
        #Convert the tree back to XML and save
        fc_md.xml = ET.tostring(tree)
    except:
        warn("Could not fix order of fields within metadata")
        #If something goes wrong, set the fields to the backup so no metadata actually gets deleted
        fc_md.xml = treeBackup
    fc_md.save()

def AddDomainsToMD(fc):
    fc_md = arcpy.metadata.Metadata(fc)
    fields = [field for field in arcpy.ListFields(fc)]
    upperDomainFields = [field.name.upper() for field in fields if field.domain]
    upperDomainNames = [field.domain.upper() for field in fields if field.domain]
    msg(upperDomainFields)

    allDomains = arcpy.da.ListDomains(getWorkspace(fc))
    msg([domain.name for domain in allDomains])
    relevantDomains = [domain for domain in allDomains if domain.name.upper() in upperDomainNames]
    relevantDomainNamesUpper = [domain.name.upper() for domain in relevantDomains]
    msg(relevantDomainNamesUpper)

    tree = ET.fromstring(fc_md.xml)
    fieldMetadataList = tree.find("eainfo").find("detailed").findall("attr") #Get the list of fields
    if fieldMetadataList:
        for attr in fieldMetadataList:
            name = attr.findtext("attrlabl")
            if name.upper() in upperDomainFields:
                domain = relevantDomains[relevantDomainNamesUpper.index(upperDomainNames[upperDomainFields.index(name.upper())])]
                domainCodedValues = domain.codedValues
                if domainCodedValues and not attr.find("attrdomv"):
                    msg(name)
                    #Add the basic listing
                    attrdomv = ET.Element("attrdomv")
                    codesetd = ET.Element("codesetd")

                    codesetn = ET.Element("codesetn")
                    codesetn.text = domain.name
                    codesetd.append(codesetn)

                    codesets = ET.Element("codesets")
                    codesets.text = "-"
                    codesetd.append(codesets)

                    attrdomv.append(codesetd)
                    attr.append(attrdomv)

                    #Add the coded values
                    attrdomv = ET.Element("attrdomv")
                    for value in domainCodedValues.keys():
                        edom = ET.Element("edom")

                        edomv = ET.Element("edomv")
                        edomv.text = value
                        edom.append(edomv)

                        edomvd = ET.Element("edomvd")
                        if domainCodedValues[value] != value:
                            edomvd.text = domainCodedValues[value]
                        else:
                            edomvd.text = "-"
                        edom.append(edomvd)

                        edomvds = ET.Element("edomvds")
                        edomvds.text = "-"
                        edom.append(edomvds)

                        attrdomv.append(edom)
                    attr.append(attrdomv)
                    
                    # PrintXML(attr, 1)
                else:
                    msg(name)
        fc_md.xml = ET.tostring(tree)
        fc_md.save()
    else:
        msg('Error with how the program finds field metadata, fix the AddDomainsToMD function')
        raise SystemExit
    return

def CheckFieldMDQuality(fc): 
    """Check if there are duplicate or missing field metadata values in 'fc'"""
    fc_md = arcpy.metadata.Metadata(fc)
    fields = arcpy.ListFields(fc)
    fieldNames = [field.name for field in fields]
    upperFields = [field.upper() for field in fieldNames]
    upperDomainFields = [field.name.upper() for field in fields if field.domain]
    unusedFields = upperFields.copy() #Check for missing fields in metadata
    usedFields = [] #Check for duplicate filds in metadata

    tree = ET.fromstring(fc_md.xml)
    try:
        fieldMetadataList = tree.find("eainfo").find("detailed").findall("attr") #Get the list of fields
    except:
        error("Issue with reading field metadata. Metadata May not exist for Fields")
        return
    if fieldMetadataList:
        #Find duplicate, missing, or improperly-named fields from the metadata
        for attr in fieldMetadataList:
            name = attr.findtext("attrlabl")
            uName = name.upper()
            msg("Checking: " + str(name))
            if uName in usedFields:
                warn(""+str(name) + " is a duplicate field within the metadata")
            else:
                if uName in upperFields:
                    if name not in fieldNames:
                        warn(""+str(name) +" should be " + str(fieldNames[upperFields.index(uName)]))
                    unusedFields.remove(uName)
                    usedFields.append(uName)
                else:
                    warn(""+str(name) +" is not in the list of fields, possibly should be deleted")

            if uName in upperDomainFields:
                realDomainName = fields[upperFields.index(uName)].domain
                domainNameAttr = [(a) for a in attr.findall("attrdomv") if a.find("codesetd")]
                if (domainNameAttr):
                    mdDomainName = domainNameAttr[0].find("codesetd").find("codesetn").text
                    if realDomainName != mdDomainName:
                        warn("Domain: "+mdDomainName + " Should be " + realDomainName)
                    else:
                        msg("\tDomain: "+mdDomainName)
                        domainValuesAttr = [(a) for a in attr.findall("attrdomv") if not a.find("codesetd")][0]
                        edoms = domainValuesAttr.findall("edom")
                        if edoms:
                            msg("\tDomain Values (Separate Values):")
                            for edom in edoms:
                                msg("\t\t" + str(edom.find("edomv").text))
                                edomvd = edom.find("edomvd")
                                # msg(edomvd.text)
                                if edomvd is None or edomvd.text == "-":
                                    warn("\tField Description is placeholder")
                                edomvds = edom.find("edomvd")
                                if edomvds is None or edomvds.text == "-":
                                    warn("\tField Source is placeholder")
                        else:
                            udom = domainValuesAttr.find("udom")
                            if udom is not None:
                                msg("\tDomain Values (List): " + str(udom.text))
                            else:
                                warn("Domain Exists in metadata but is unpopulated")
                else:
                    warn("Domain needed within metadata")
        if unusedFields:
            warn("The following fields do not have metadata: "+ str(unusedFields))
    else:
        error('Error with how the program finds field metadata, fix the CheckFieldMDQuality function')
        raise SystemExit
    #Convert the tree back to XML and save
    fc_md.xml = ET.tostring(tree)
    fc_md.save()

def CheckMDQuality(fc):
    fc_md = arcpy.metadata.Metadata(fc)

    tree = ET.fromstring(fc_md.xml)
    try:
        desc = tree.find("dataIdInfo").find("idAbs")
        if desc == "-":
            warn("Description is placeholder")
    except:
        error("No Description Found")
        return
    # PrintXML(tree.find("dataIdInfo"))
    return

def AlterField(fc, fieldName, newFieldName=None, newFieldAlias=None, newFieldType=None, newFieldlength=None, fieldIsNullable = None, clearFieldAlias = False):
    #Get the existing verison of the field in question
    existingFields = arcpy.ListFields(fc)
    field = [field for field in existingFields if field.name.upper() == fieldName.upper()]
    if len(field) != 1:
        error(str(fieldName) + "cannot be found within "+ str(fc))
        raise SystemExit
    oldField = field[0]

    # Set input values appropriately
    if not newFieldName:
        newFieldName = fieldName
    if not newFieldAlias and not clearFieldAlias:
        newFieldAlias = oldField.aliasName
    oldFieldType = oldField.type.upper().replace(" ", "")
    if not newFieldType:
        newFieldType = oldFieldType
    newFieldType = newFieldType.upper()
    fieldTypesList ={"INTEGER":"LONG", "STRING":"TEXT", "SMALLINTEGER": "SHORT"}
    if newFieldType in fieldTypesList: 
        newFieldType = fieldTypesList[newFieldType]
    if oldFieldType in fieldTypesList: 
        oldFieldType = fieldTypesList[oldFieldType]
    if not newFieldlength:
        newFieldlength = oldField.length
    newFieldlength = int(newFieldlength)
    if not fieldIsNullable:
        fieldIsNullable = oldField.isNullable
            
    # msg((oldFieldType))
    # msg((newFieldType))
    lengthChange = (newFieldlength and (newFieldType == "TEXT" or newFieldType == "BLOB") and ((oldFieldType != "TEXT" or oldFieldType != "BLOB") or oldField.length > newFieldlength))
    typeChange = (oldFieldType != newFieldType)
    #Check if recreating the field is needed, or if the standard alter field function will work
    if (int(arcpy.management.GetCount(fc)[0])> 0) and (lengthChange or typeChange):
        #Create temporary field
        tempFieldName = fieldName + "__1"

        # Add a new field with new settings
        arcpy.AddField_management(fc, tempFieldName, newFieldType, oldField.precision, oldField.scale, newFieldlength, newFieldAlias, fieldIsNullable, oldField.required, oldField.domain)

        try:
            # Copy values from the old field to the new field
            with arcpy.da.UpdateCursor(fc, [fieldName, tempFieldName]) as cursor:
                newType = type(newFieldType)
                for row in cursor:
                    if row[0] is not None:
                        newValue = row[0]
                        if lengthChange:
                            newValue = newType(newValue)
                            newValue = newValue[:newFieldlength]
                        row[1] = newValue
                    cursor.updateRow(row)
        except Exception as e:
            error("Program could not alter field " + str(fieldName) + " as specified")
            error(str(e))
            arcpy.DeleteField_management(fc, tempFieldName) #Remove new field if program could not create it properly
            raise SystemExit

        # Delete the old field
        arcpy.DeleteField_management(fc, fieldName)

        # Rename the new field to the old field's name
        arcpy.AlterField_management(fc, tempFieldName, newFieldName)
    else:
        arcpy.AlterField_management(fc, fieldName, newFieldName, newFieldAlias, field_is_nullable=fieldIsNullable, clear_field_alias=clearFieldAlias)
    
    return

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Add Data Standards + Metadata"
        self.alias = "Add Data Standards + Metadata"

        # List of tool classes associated with this toolbox
        self.tools = [AddDataStandardsToExistingFC, JustAddMetadata, CheckMetadataQuality, TestingTool]

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

    def getParameterDomainfilters(self, parameters, index):
        domains = arcpy.da.ListDomains(getWorkspace(parameters[index].valueAsText))
        testStr = ""
        if domains:
            domainNames = [domain.name for domain in domains]

            fieldNames = ["UNITCODE", "UNITNAME", "GROUPCODE", "GROUPNAME", "REGIONCODE"]
            paramRange = list(range(3, 8))
            fields = arcpy.ListFields(parameters[index].valueAsText)
            domainMatch = []
            for i in range(len(paramRange)):
                domainMatch = [domains[domainNames.index(field.domain)] for field in fields if field.name.upper() == fieldNames[i] and field.domain]
                # testStr+=("("+str(paramRange[i])+": "+str(fieldMatch)+")")
                if domainMatch:
                    if domainMatch[0].domainType == "CodedValue":
                        domainDict = domainMatch[0].codedValues
                        values = list(domainDict.keys())
                        domainFilter = values.copy()
                        for j in range(len(domainFilter)):
                            value = domainFilter[j]
                            if domainDict[value] != value:
                                domainFilter[j] +=" | "+str(domainDict[value])
                            # testStr += str(value)+ ", "
                        parameters[paramRange[i]].filter.list = domainFilter
                        # testStr+=("("+str(paramRange[i])+": "+str(list(domainDict.keys()))+")")
                        # testStr += str(domainFilter)
        if parameters[-1].value:
            parameters[-1].value += testStr
        else:
            parameters[-1].value = testStr

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        EmptyFieldParam = ["", False, "", ""]

        if parameters[1].valueAsText:
            if parameters[0].valueAsText:
                oldFieldNames = arcpy.ListFields(parameters[0].valueAsText)
                newFieldNames = arcpy.ListFields(parameters[1].valueAsText)

                #Get existing values within 'Existing Fields' parameter
                existingInputs = []
                if parameters[8].value: 
                    existingInputs = [row[1:] for row in parameters[8].value]
                while(len(existingInputs) > 0 and existingInputs[-1] == EmptyFieldParam[1:]):
                    existingInputs.pop()

                #Find fields that are in both the FC and the Template
                oldFieldNamesUpper = [f.name.upper() for f in oldFieldNames if f.type not in removedFieldTypes] 
                newFieldNamesUpper = [f.name.upper() for f in newFieldNames if f.type not in removedFieldTypes]
                MatchFieldNames = list(set(oldFieldNamesUpper).intersection(set(newFieldNamesUpper)))
                
                #Put the list of matching names into the "Existing Fields" Parameter, or disable the parameter
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
                pass

            #Check for domains from existing source
            

            if parameters[0]:
                self.getParameterDomainfilters(parameters, 0)

            self.getParameterDomainfilters(parameters, 1)
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[8].value and parameters[8].enabled:
            #Check if the "Existing Values" Parameter had values in it before the read-only sub-parameters were changed, leaving behind blank read-only sub-parameters
            if parameters[8].value[-1][0] == "":
                parameters[8].setWarningMessage("Warning: too many Values in this parameter. Extraneous inputs will be ignored")
                
            #Check for Issues with the parameters that will not have a copy made of them
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
        msg(messages)
        fcBase = parameters[0].valueAsText
        fc = arcpy.da.Describe(fcBase)['catalogPath']
        template = parameters[1].valueAsText
        create_backup = parameters[2].value
        unit_code = parameters[3].valueAsText
        if type(unit_code) == str and "|" in unit_code: #If the new value had a line displaying the key/value pair of the domain, remove the value
            unit_code = unit_code.split("|")[0][:-1]
        unit_name = parameters[4].valueAsText
        if type(unit_name) == str and "|" in unit_name: #If the new value had a line displaying the key/value pair of the domain, remove the value
            unit_name = unit_name.split("|")[0][:-1]
        group_code = parameters[5].valueAsText
        if type(group_code) == str and "|" in group_code: #If the new value had a line displaying the key/value pair of the domain, remove the value
            group_code = group_code.split("|")[0][:-1]
        group_name = parameters[6].valueAsText
        if type(group_name) == str and "|" in group_name: #If the new value had a line displaying the key/value pair of the domain, remove the value
            group_name = group_name.split("|")[0][:-1]
        region_code = parameters[7].valueAsText
        if type(region_code) == str and "|" in region_code: #If the new value had a line displaying the key/value pair of the domain, remove the value
            region_code = region_code.split("|")[0][:-1]
        field_renamings = parameters[8].value

        # get the gdb where the fc lives
        gdb = getWorkspace(fc)

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

        #Rename fields as needed
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
                                AlterField(fc, realFld, newName, newAlias)
                                EditFieldMDName(fc, realFld, newName, newAlias)
                            except Exception as e:
                                error(str(e))
                                error("Name cannot be set to "+str(newName)+". Ending Program")
                                raise SystemExit
                        else:
                            arcpy.AddError("No new name given for renamed fields")
                            raise SystemExit
            fc_md = arcpy.metadata.Metadata(fc)
            fc_md.synchronize()

        #Override existing metadata
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
                    AlterField(fc, realFld, fld.name, fld.aliasName, fld.type, fld.length)#=======================================================================================================
                except Exception as e:
                    error("{4} {5}".format(fc, realFld, fld.name, fld.aliasName, fld.type, fld.length))
                    error(str(e))
                    error("Name cannot be set to "+str(fld.name))
                if fld.domain:
                    try: 
                        arcpy.management.AssignDomainToField(fc, realFld, fld.domain)
                    except:
                        warn("Domain cannot be set to "+str(fld.domain))
                        

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

        #Add new metadata
        msg('... Adding field metadata ...')

        AddMD(fc, template)

        msg('... ensuring domains were added to metadata...')

        AddDomainsToMD(fc)

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

        template = arcpy.Parameter(
                displayName = "Source Feature Class",
                name = "template",
                datatype = "DEFeatureClass",
                parameterType = "Required",
                direction = "Input")
        
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
        if parameters[0].valueAsText and parameters[1].valueAsText:
            oldFields = arcpy.ListFields(parameters[0].valueAsText)
            oldFieldNamesUpper = [field.name.upper() for field in oldFields]
            newFields = arcpy.ListFields(parameters[1].valueAsText)
            newFieldNamesUpper = [field.name.upper() for field in newFields]

            errorMessage = ""
            for field in newFieldNamesUpper:
                if field not in oldFieldNamesUpper:
                    errorMessage += str(field) +" is not in the existing fields list. Please add the field or use the add data standards tool\n"
            if errorMessage:
                parameters[0].setErrorMessage(errorMessage)
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        
        fcBase = parameters[0].valueAsText
        fc = arcpy.da.Describe(fcBase)['catalogPath']
        template = parameters[1].valueAsText
        gdb = getWorkspace(fc)

        fc_md = arcpy.metadata.Metadata(fc)
        fc_md.synchronize()

        fcFields = arcpy.ListFields(fc)
        fcFieldsUpper = [f.name.upper() for f in arcpy.ListFields(fc)]
        tempFieldsUpper = [f.name.upper() for f in arcpy.ListFields(template)]
        existingFields = [field for field in fcFieldsUpper if field in tempFieldsUpper]

        existingFields.extend([f.name.upper() for f in fcFields if f.type in removedFieldTypes and f.name.upper() in tempFieldsUpper]) #Override metadata for removed field types
        if len(existingFields) > 0:
            DeleteFieldsFromMD(fc, existingFields)


        msg('... Adding field metadata ...')

        AddMD(fc, template)

        msg('... Fixing field metadata formatting...')
        FixFieldMDCapitalization(fc)
        FixFieldMDOrder(fc)

        msg('... Tool complete ...')
        
        return

class CheckMetadataQuality(object):

    def __init__(self):
        self.label = "Check Metadata Quality"
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
        if arcpy.metadata.Metadata(fc):
            CheckMDQuality(fc)
            CheckFieldMDQuality(fc)
        else:
            error("No Metadata Found")
        return

class TestingTool(object):
    def __init__(self):
        self.label = "Add Domains to MD"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        params = [arcpy.Parameter(
                displayName = "Feature Class",
                name = "Feature Class",
                datatype = "GPTableView",
                parameterType = "Required",
                direction = "Input"),
            # arcpy.Parameter(
            #     displayName = "Field",
            #     name = "Field",
            #     datatype = "Field",
            #     parameterType = "Required",
            #     direction = "Input"),
            # arcpy.Parameter(
            #     displayName = "Type",
            #     name = "Type",
            #     datatype = "String",
            #     parameterType = "Optional",
            #     direction = "Input"),
            # arcpy.Parameter(
            #     displayName = "Length",
            #     name = "Length",
            #     datatype = "GPLong",
            #     parameterType = "Optional",
            #     direction = "Input"),
        ]
        # params[1].parameterDependencies = [params[0].name]
        # params[2].filter.list=["Blob","BigInteger","Date","DateOnly","Double","Geometry","GlobalID","Guid","Integer","OID","Raster","Single","SmallInteger","String","TimeOnly","TimestampOffset"]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        fc = parameters[0].valueAsText
        AddDomainsToMD(fc)
        return