# -*- coding: utf-8 -*-

#Made by Claire Hallock in 2024-2025
#Last updated 3/13/2025

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
    """Get the containing workspace of the specified layer/table/etc."""
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

def addDefaultsToNewField(fc, fieldName, defaultValue):
    """Performs arcpy.management.AssignDefaultToField and adds the default value to any rows that already existed in the attribute table"""
    arcpy.management.AssignDefaultToField(fc, fieldName, defaultValue)

    #Add values to table
    with arcpy.da.UpdateCursor(fc, [fieldName]) as cursor:
        for row in cursor:
            # if not row[0]:
            row[0] = defaultValue
            cursor.updateRow(row)

def ImportUnsyncedMetadata(Sourcefc, Destinationfc):
    if arcpy.metadata.Metadata(Sourcefc):
        SourceMD = arcpy.metadata.Metadata(Sourcefc)
        DestinationMD = arcpy.metadata.Metadata(Destinationfc)
        DestinationMD.xml = SourceMD.xml
        DestinationMD.save()
    else:
        error("No Metadata Found in Source.")
    return

def CreateBackup(fc, suffix = "_original"):
    gdb = getWorkspace(fc)
    fc_name = fc.split("\\")[-1]

    msg('... Making backup copy of original feature class ...')
    backup_fc_name = str(fc_name) + str(suffix)
    
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
        
        #Make sure metadata doesn't get synced while creating a copy
        ImportUnsyncedMetadata(fc, backup_fc_name)

def AddMDFromTemplate(fc, template):
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
        error("Not a valid list of fields to delete from metadata. Check DeleteFieldsFromMD")
        raise SystemExit

def DeleteFieldFromMD(fc, name):
    """Delete the field in 'name' from the metadata in 'fc'"""
    DeleteFieldsFromMD(fc, [name])

def DeleteDuplicateFieldsFromMD(fc, fieldName, duplicateNumberList):
    """Delete duplicates of the field names "fieldName" from the fc. duplicateNumberList is a list that holds the integer representation of the index of each duplicate, where the first existing version of the field is numbered 0, and all subsequent versions (duplicates) are labelled 1,2,3,..."""
    fc_md = arcpy.metadata.Metadata(fc)

    tree = ET.fromstring(fc_md.xml)

    fieldMetaDataRoot = tree.find("eainfo").find("detailed")
    fieldMetadataList = fieldMetaDataRoot.findall("attr") #Get the list of fields
    if fieldMetadataList:
        duplicateCount = 0
        deletedList = []
        #Go through each field in MD To look for dupes of fieldName, then delete them if the index is found within duplicateNumberList
        for attr in fieldMetadataList:
            if attr.findtext("attrlabl").upper() == fieldName.upper():
                if duplicateCount in duplicateNumberList:
                    msg("Deleting old metadata for: "+str(attr.findtext("attrlabl")))
                    fieldMetaDataRoot.remove(attr)
                    deletedList.append(duplicateCount)
                duplicateCount += 1
        msg("Found " + str(duplicateCount - 1) + " duplicates of field '" + str(fieldName) +"'. Deleted duplicates numbered: "+ str(deletedList))
        fc_md.xml = ET.tostring(tree)
        fc_md.save()
    else:
        error('Error with how the program finds field metadata, fix the DeleteDuplicateFieldsFromMD function')

def AddFieldToMD(fc, name):
    """Add a Field name "name" to Metadata in "fc". No other information is added other than the field name."""
    fc_md = arcpy.metadata.Metadata(fc)

    tree = ET.fromstring(fc_md.xml)

    #Check if the field already exists in the metadata and should not be added
    fieldMetadataList = tree.find("eainfo").find("detailed").findall("attr")
    if fieldMetadataList:
        for attr in fieldMetadataList:
            fieldName = attr.findtext("attrlabl")
            if fieldName.upper() == name.upper():
                warn("Tried to add field " + str(name) +" but it already existed")
                return
    
    #Create the md field and add it to metadata
    detailed = tree.find("eainfo").find("detailed")
    attr = ET.Element("attr")
    attrlabl = ET.Element("attrlabl")
    attrlabl.text = name

    attr.append(attrlabl)
    detailed.append(attr)

    fc_md.xml = ET.tostring(tree)
    fc_md.save()

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
                warn(str(field) + " does not have corresponding metadata")
        if fieldMDNames: #If not all fields were added via parsing through 'fieldOrder', add them to the end of the list
            fieldMetaDataRoot.extend(fieldMetadataList)
            warn(str(fieldMDNames) + " were added to the end as they were not found within the fields list.") 
        #Convert the tree back to XML and save
        fc_md.xml = ET.tostring(tree)
    except:
        warn("Could not fix order of fields within metadata")
        #If something goes wrong, set the fields to the backup so no metadata actually gets deleted
        fc_md.xml = treeBackup
    fc_md.save()

def RenameFieldMetadata(fc, oldName, newName):
    fc_md = arcpy.metadata.Metadata(fc)

    tree = ET.fromstring(fc_md.xml)
    fieldMetadataList = tree.find("eainfo").find("detailed").findall("attr") #Get the list of fields currently in metadata
    if fieldMetadataList:
        for attr in fieldMetadataList:
            fieldName = attr.findtext("attrlabl")
            if fieldName.upper() == oldName.upper():
                attrlabl = attr.find("attrlabl")
                attrlabl.text = newName
                fc_md.xml = ET.tostring(tree)
                fc_md.save()
                return
    else:
        warn("No metadata found while using the RenameFieldMetadata function")
    return

def FixFieldMDDescsEtc(fc, fieldDescDict = {}):
    """Update Field Metadata Descriptions in fc to match descriptions provided in fieldDescDict.
    
    Additionally, adds placeholders to other needed field metadata values such as Source"""
    fc_md = arcpy.metadata.Metadata(fc)

    tree = ET.fromstring(fc_md.xml)
    fieldMetadataList = tree.find("eainfo").find("detailed").findall("attr") #Get the list of fields currently in metadata
    if fieldMetadataList:
        for attr in fieldMetadataList:
            fieldName = attr.findtext("attrlabl")
            if fieldName:
                #Description
                attrdef = attr.find("attrdef")
                #Exists
                if attrdef is not None:
                    if fieldDescDict:#Add inputted value if needed
                        if fieldName.upper() in fieldDescDict.keys():
                            attrdef.text = fieldDescDict[fieldName.upper()]
                            if not attrdef.text:
                                attrdef.text = "-"
                        else:
                            warn("Tried to fix Description of '" + str(fieldName) +"' but couldn't find the description")
                    else:
                        #Doesn't have an existing value
                        if not attrdef.text:
                            attrdef.text = "-"
                #Doesn't Yet Exist
                else:
                    attrdef = ET.Element("attrdef")
                    if fieldDescDict:#Add inputted value if needed
                        if fieldName.upper() in fieldDescDict.keys():
                            attrdef.text = fieldDescDict[fieldName.upper()]
                            if not attrdef.text:
                                attrdef.text = "-"
                        else:
                            warn("Tried to add Description to '" + str(fieldName) +"' but couldn't find the description")
                    else:
                        attrdef.text = "-"
                    attr.append(attrdef)

                #Source
                attrdefs = attr.find("attrdefs")
                #Exists
                if attrdefs is not None:
                    #Doesn't have an existing value
                    if not attrdefs.text:
                        attrdefs.text = "-"
                #Doesn't Yet Exist
                else:
                    attrdefs = ET.Element("attrdefs")
                    attrdefs.text = "-"
                    attr.append(attrdefs)

                #Description of Values/Domain
                attrdomv = attr.find("attrdomv")
                if attrdomv is not None:
                    udom = attrdomv.find("udom")
                    if udom is not None and udom.text is None:
                        #Exists
                        if udom is not None:
                            #Doesn't have an existing value
                            if not udom.text:
                                udom.text = "-"
                        #Doesn't Yet Exist
                        else:
                            udom = ET.Element("udom")
                            udom.text = "-"
                            attrdomv.append(udom)
                else: #Need to create attrdomv
                    attrdomv = ET.Element("attrdomv")
                    udom = ET.Element("udom")
                    udom.text = "-"
                    attrdomv.append(udom)
                    attr.append(attrdomv)

    fc_md.xml = ET.tostring(tree)
    fc_md.save()

def AddSeparateDomainValues(value, domainCodedValues, edomvdValue = None, edomvdsValue = None):
    """Within metadata, creates an individual "edom" to represent a specific 'value' in a domain. This value is then compared against the dict 'domainCodedValues' to see if there is a separate alias for the value.
    
    edomvdValue represents the description of that specific value within the domain, and edomvdsValue contains the source for that description"""
    edom = ET.Element("edom")

    edomv = ET.Element("edomv")
    edomv.text = str(value)
    edom.append(edomv)
    
    #If no specified description, check for an alias to use as the placeholder description
    edomvd = ET.Element("edomvd")
    if not edomvdValue:
        if domainCodedValues[value] != value:
            edomvdValue = domainCodedValues[value]
        else:
            edomvdValue = "-"
    edomvd.text = str(edomvdValue)
    edom.append(edomvd)

    edomvds = ET.Element("edomvds")
    if not edomvdsValue:
        edomvdsValue = "-"
    edomvds.text = str(edomvdsValue)
    edom.append(edomvds)
    return edom

def RemoveOldMDDomain(attr):
    """Given an attr Element of an Element Tree, remove all domain values."""
    if type(attr) == ET.Element and attr.tag == "attr":
        for attrdomvOld in attr.findall("attrdomv"):
            if attrdomvOld.find("edom") is not None or attrdomvOld.find("udom") is not None or attrdomvOld.find("rdom") is not None:
                attr.remove(attrdomvOld)
    else:
        error("Tried to remove domain from non-attr value")

def AddDomainsToMD(fc, valueDescriptions = None):
    """Add All Domains to metadata if they don't exist"""
    #Get basic info about fields
    fc_md = arcpy.metadata.Metadata(fc)
    fields = [field for field in arcpy.ListFields(fc)]
    upperDomainFields = [field.name.upper() for field in fields if field.domain]
    upperDomainNames = [field.domain.upper() for field in fields if field.domain]

    allDomains = arcpy.da.ListDomains(getWorkspace(fc))
    relevantDomains = [domain for domain in allDomains if domain.name.upper() in upperDomainNames]
    relevantDomainNamesUpper = [domain.name.upper() for domain in relevantDomains]

    #Create a metadata tree and check for existing domain
    tree = ET.fromstring(fc_md.xml)
    fieldMetadataList = tree.find("eainfo").find("detailed").findall("attr") #Get the list of fields currently in metadata
    if fieldMetadataList:
        for attr in fieldMetadataList:
            fieldName = attr.findtext("attrlabl")
            if fieldName.upper() in upperDomainFields: #Find fields in metadata that have domains
                domain = relevantDomains[relevantDomainNamesUpper.index(upperDomainNames[upperDomainFields.index(fieldName.upper())])]

                domainCodedValues = None
                domainRange = None
                if domain.domainType == "CodedValue":
                    domainCodedValues = domain.codedValues
                else:
                    domainRange = domain.range
                if attr.find("attrdomv") is not None:
                    msg(fieldName)
                    
                    #Add the basic listing
                    if [a.find("codesetd") for a in attr.findall("attrdomv")] is None:
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
                    if (not valueDescriptions and [a.find("edom") for a in attr.findall("attrdomv")] is not None) or (valueDescriptions and fieldName in valueDescriptions.keys()): #only add new domain if specified in valueDescriptions or if domain does not already exist in metadata
                        #If using separate values
                        if (not valueDescriptions and domainCodedValues) or valueDescriptions[fieldName] == "Use Separate Values": 
                            attrdomv = ET.Element("attrdomv")
                            MDattrdomvs = attr.findall("attrdomv")
                            MDedoms = [a.findall("edom") for a in MDattrdomvs if a is not None]
                            valuesInMD = {a.find("edomv").text.split(" (default)")[0]:[a.findtext("edomvd"), a.findtext("edomvds")] for aa in MDedoms for a in aa if aa is not None and a is not None}
                            # msg(valuesInMD)
                            msg("\t"+str(domainCodedValues))
                            for value in domainCodedValues.keys():
                                if str(value) in valuesInMD.keys():
                                    edomvdValue = valuesInMD[str(value)][0]
                                    edomvdsValue = valuesInMD[str(value)][1]
                                    attrdomv.append(AddSeparateDomainValues(value, domainCodedValues, edomvdValue, edomvdsValue))
                                    del valuesInMD[str(value)]
                                    msg("\t\t"+str(value))
                                else:
                                    attrdomv.append(AddSeparateDomainValues(value, domainCodedValues))
                            if valuesInMD:
                                for value in valuesInMD.keys():
                                    attrdomv.append(AddSeparateDomainValues(value, domainCodedValues, valuesInMD[value][0], valuesInMD[value][1]))
                                warn("Extra metadata domain Values: " + str(valuesInMD)+ " in field " + str(fieldName))
                                
                            #Delete other forms of domain metadata before adding new one
                            RemoveOldMDDomain(attr)
                            attr.append(attrdomv)
                        
                        #If using list of keys
                        elif valueDescriptions[fieldName] == "Use List of Keys":
                            attrdomv = ET.Element("attrdomv")
                            udom = ET.Element("udom")
                            udom.text = ";\n".join(domainCodedValues)
                            attrdomv.append(udom)
                            #Delete other forms of domain metadata before adding new one
                            RemoveOldMDDomain(attr)
                            attr.append(attrdomv)

                        #If using list of keys/values
                        elif valueDescriptions[fieldName] == "Use List of Keys/Values":
                            attrdomv = ET.Element("attrdomv")
                            udom = ET.Element("udom")
                            domainValuePairs = [str(value)+"|"+str(domainCodedValues[value]) for value in domainCodedValues]
                            udom.text = ";\n".join(domainValuePairs)
                            attrdomv.append(udom)
                            #Delete other forms of domain metadata before adding new one
                            RemoveOldMDDomain(attr)
                            attr.append(attrdomv)
                        
                        #If is range domain instead of coded values
                        elif (not valueDescriptions and domainRange) or valueDescriptions[fieldName] == "Range":
                            msg(str(fieldName) + " (Range)")
                            attrdomv = ET.Element("attrdomv")
                            rdom = ET.Element("rdom")
                            rdommin = ET.Element("rdommin")
                            rdommin.text = str(domainRange[0])
                            rdommax = ET.Element("rdommax")
                            rdommax.text = str(domainRange[1])
                            rdom.append(rdommin)
                            rdom.append(rdommax)
                            attrdomv.append(rdom)
                            #Delete other forms of domain metadata before adding new one
                            RemoveOldMDDomain(attr)
                            attr.append(attrdomv)
                else:
                    msg(fieldName)
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

    upperDomainNames = [field.domain.upper() for field in fields if field.domain]
    allDomains = arcpy.da.ListDomains(getWorkspace(fc))
    relevantDomains = [domain for domain in allDomains if domain.name.upper() in upperDomainNames]
    relevantDomainNamesUpper = [domain.name.upper() for domain in relevantDomains]

    tree = ET.fromstring(fc_md.xml)
    try:
        fieldMetadataList = tree.find("eainfo").find("detailed").findall("attr") #Get the list of fields
    except:
        error("Issue with reading field metadata. Metadata May not exist for Fields")
        return
    if fieldMetadataList:
        #Find duplicate, missing, or improperly-named fields from the metadata
        for attr in fieldMetadataList:
            fieldName = attr.findtext("attrlabl")
            uName = fieldName.upper()
            msg("Checking: " + str(fieldName))
            if uName in usedFields:
                warn(""+str(fieldName) + " is a duplicate field within the metadata")
            else:
                if uName in upperFields:
                    if fieldName not in fieldNames:
                        warn(""+str(fieldName) +" should be " + str(fieldNames[upperFields.index(uName)]))
                    unusedFields.remove(uName)
                    usedFields.append(uName)
                else:
                    warn(""+str(fieldName) +" is not in the list of fields, possibly should be deleted")
            #Check if Domain is in MD
            if uName in upperDomainFields:
                realDomainName = fields[upperFields.index(uName)].domain
                domainNameAttr = [(a) for a in attr.findall("attrdomv") if a.find("codesetd")]
                if (domainNameAttr):
                    mdDomainName = domainNameAttr[0].find("codesetd").find("codesetn").text
                    if realDomainName != mdDomainName:
                        warn("Domain: "+mdDomainName + " Should be " + realDomainName)
                    else:
                        msg("\tDomain: "+mdDomainName)
                        domainValuesAttr = [(a) for a in attr.findall("attrdomv") if a.find("codesetd") is None][0]
                        edoms = domainValuesAttr.findall("edom")
                        if edoms: #Separate values
                            msg("\tDomain Values (Separate Values):")
                            for edom in edoms: #check each domain value for placeholders
                                domainValue = edom.find("edomv").text
                                msg("\t\t" + str(domainValue))
                                edomvd = edom.find("edomvd")
                                if edomvd is None or edomvd.text == "-":
                                    warn("\tDomain Value Description is placeholder")
                                edomvds = edom.find("edomvds")
                                if edomvds is None or edomvds.text == "-":
                                    warn("\tDomain Value Source is placeholder")
                        else: #List of values
                            udom = domainValuesAttr.find("udom")
                            if udom is not None:
                                msg("\tDomain Values (List): " + str(udom.text))
                            else:
                                rdom = domainValuesAttr.find("rdom")
                                if rdom is not None:
                                    rdommin = rdom.findtext("rdommin")
                                    rdommax = rdom.findtext("rdommax")
                                    if rdommin and rdommax:
                                        msg("\tRange: (" + str(rdommin) + " to " + str(rdommax) + ")")
                                    else:
                                        warn(str(fieldName) + " Range Domain has missing min or max value")
                                else:
                                    PrintXML(domainValuesAttr)
                                    warn(str(fieldName) + "Domain Exists in metadata but is unpopulated")
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

def SynchronizeMetadata(fc):
    """Run the synchronize function on the metadata found within fc"""
    try:
        fc_md = arcpy.metadata.Metadata(fc)
        fc_md.synchronize()
    except:
        warn("Could not synchronize Metadata")

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
        self.tools = [AddDataStandardsToExistingFC, JustAddMetadata, FixMetadataDomains, FixFieldMetadata, CheckMetadataQuality, ImportMetadata]#, TestingTool]

class AddDataStandardsToExistingFC(object):
    def __init__(self):
        """This tool adds data standard fields to an existing feature class."""
        self.label = "Add STANDARD Fields and their Metadata"
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
                displayName = "Existing Fields to be Overwritten",
                name = "Existing_Fields",
                datatype = "GPString",
                parameterType = "Optional",
                direction = "Input",
                multiValue=True
        )
        fieldInfo.columns = [["GPString", "Existing Field Name", "READONLY"], ["GPBoolean", "Save field from being overwritten and create separate Data Standard Field (Existing Field needs to be renamed)"], ["GPString", "New Field Name"], ["GPString", "New Field Alias"]]
        fieldInfo.enabled = False
        
        params = [fc, template, createBackup, default_unit_code, default_unit_name, default_group_code, default_group_name, default_region_code, fieldInfo]#, arcpy.Parameter(
                # displayName = "Test String",
                # name = "String",
                # datatype = "GPString",
                # parameterType = "Optional",
                # direction = "Input")]
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
        # if parameters[-1].value:
        #     parameters[-1].value += testStr
        # else:
        #     parameters[-1].value = testStr

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
                    if not row[1]:
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

        #Create backup if needed
        if create_backup:
            CreateBackup(fc)

        #Rename fields as specified to prevent overrides
        if field_renamings:
            msg(f'... Rename data standard fields that already exist in {fc_name} ...')

            # compare fields, find similar
            FCfield_names = [f.name.upper() for f in arcpy.ListFields(fc)] 
            FCRealfield_names = [f.name for f in arcpy.ListFields(fc)] #Is this needed?

            msg('... Renaming existing fields...')
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

        #Delete existing metadata specified to be overridden
        existingFields = [row[0] for row in field_renamings if not row[1]]
        fcFields = arcpy.ListFields(fc)
        tempFieldsUpper = [f.name.upper() for f in arcpy.ListFields(template)]

        existingFields.extend([f.name.upper() for f in fcFields if f.type in removedFieldTypes and f.name.upper() in tempFieldsUpper]) #Override metadata for removed field types
        if len(existingFields) > 0:
            DeleteFieldsFromMD(fc, existingFields)
        
        # get domains in template gdb
        template_gdb = getWorkspace(template)
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

            # create the field if it does not exist
            if fld.name.upper() not in existingFields:
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
            else: #Or rename if properly if it does
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
                addDefaultsToNewField(fc, "UNITCODE", unit_code)
            if unit_name and fld.name == "UNITNAME":
                addDefaultsToNewField(fc, "UNITNAME", unit_name)
            if group_code and fld.name == "GROUPCODE":
                addDefaultsToNewField(fc, "GROUPCODE", group_code)
            if group_name and fld.name == "GROUPNAME":
                addDefaultsToNewField(fc, "GROUPNAME", group_name)
            if region_code and fld.name == "REGIONCODE":
                addDefaultsToNewField(fc, "REGIONCODE", region_code)

        #Add new metadata
        msg('... Adding field metadata ...')

        AddMDFromTemplate(fc, template)

        # msg('... ensuring domains were added to metadata...')

        # AddDomainsToMD(fc)

        msg('... Fixing field metadata formatting...')
        FixFieldMDCapitalization(fc)
        FixFieldMDOrder(fc)

        msg('... Tool complete ...')
        
        return

class JustAddMetadata(object):
    def __init__(self):
        """This tool adds metadata for the data standards to the data standard metadata."""
        self.label = "Add Metadata to Existing STANDARD Fields"
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

        fcFields = arcpy.ListFields(fc)
        fcFieldsUpper = [f.name.upper() for f in arcpy.ListFields(fc)]
        tempFieldsUpper = [f.name.upper() for f in arcpy.ListFields(template)]
        existingFields = [field for field in fcFieldsUpper if field in tempFieldsUpper]

        existingFields.extend([f.name.upper() for f in fcFields if f.type in removedFieldTypes and f.name.upper() in tempFieldsUpper]) #Override metadata for removed field types
        if len(existingFields) > 0:
            DeleteFieldsFromMD(fc, existingFields)


        msg('... Adding field metadata ...')

        AddMDFromTemplate(fc, template)

        msg('... Fixing field metadata formatting...')
        FixFieldMDCapitalization(fc)
        FixFieldMDOrder(fc)

        msg('... Tool complete ...')
        
        return

MDFieldParamIndex = 1
MDWithoutFieldParamIndex = 2
MissingFieldsParamIndex = 3
MissingFieldsListParamIndex = 4

class FixFieldMetadata(object):
    
    def __init__(self):
        """This tool checks and fixes some common metadata errors."""
        self.label = "Fix Fields Metadata"
        self.description = "This tool checks and fixes some common metadata errors"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        fc = arcpy.Parameter(
                displayName = "Destination Feature Class",
                name = "fc",
                datatype = "GPTableView",
                parameterType = "Required",
                direction = "Input")
        
        fieldOptions = arcpy.Parameter(
                displayName = "Metadata Field Options",
                name = "FieldOptions",
                datatype = "GPString",
                parameterType = "Optional",
                direction = "Input",
                multiValue=True
        )

        fieldOptions.columns = [["GPString", "Field Name", "READONLY"], ["GPString", "New Description value"]]
        fieldOptions.enabled = False

        spareMetadata = arcpy.Parameter(
                displayName = "Metadata Without Fields",
                name = "MetadataWithoutFields",
                datatype = "GPString",
                parameterType = "Optional",
                direction = "Input",
                multiValue=True
        )
        spareMetadata.columns = [["GPString", "Field Name", "READONLY"], ["GPString", "Description", "READONLY"], ["GPString", "Rename to existing field?"], ["GPBoolean", "If not renaming, Should this be deleted?"]]
        spareMetadata.enabled = False

        missingFields = arcpy.Parameter(
                displayName = "Fields that will be added to Metadata",
                name = "FieldswithoutMetadata",
                datatype = "GPString",
                parameterType = "Optional",
                direction = "Input",
                multiValue=True
        )
        missingFields.columns = [["GPString", "Field Name", "READONLY"], ["GPString", "Description (Optional)"]]
        missingFields.enabled = True

        missingFieldsList = arcpy.Parameter(
                displayName = "MissingFieldsList",
                name = "Fields without Metadata List",
                datatype = "GPString",
                parameterType = "Optional",
                direction = "Input",
                multiValue=True
        )
        missingFieldsList.enabled = False
        missingFieldsList.columns = [["GPString", "Field Name", "READONLY"]]
        
        params = [fc, fieldOptions, spareMetadata, missingFields, missingFieldsList]#, arcpy.Parameter(
                # displayName = "Test String",
                # name = "String",
                # datatype = "GPString",
                # parameterType = "Optional",
                # direction = "Input")]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if parameters[0].valueAsText:
            fcBase = parameters[0].valueAsText
            fc = arcpy.da.Describe(fcBase)['catalogPath']

            fields = [field for field in arcpy.ListFields(fc)]

            if not parameters[0].hasBeenValidated:
                parameters[MDFieldParamIndex].enabled = True

                #Create var to store info  to be used in param updating
                existingMetadataFieldInfo = {}

                #Get tree of existing infomation within metadata
                fc_md = arcpy.metadata.Metadata(fc)
                fc_tree = ET.fromstring(fc_md.xml)

                #
                uMDNames = []

                #Use the tree to get information about existing metadata
                eainfoTree = fc_tree.find("eainfo")
                if eainfoTree is not None:
                    treeDetailed = eainfoTree.find("detailed")
                    if treeDetailed is not None:
                        fieldMetadataList = treeDetailed.findall("attr") #Get the list of fields
                        if fieldMetadataList:
                            for attr in fieldMetadataList:
                                fieldName = attr.findtext("attrlabl")

                                #Getting the name of the field in case
                                fieldNameDesignation = ""
                                if fieldName.upper() not in existingMetadataFieldInfo.keys():
                                    fieldNameDesignation = fieldName.upper()
                                else:
                                    #Account for duplicate values
                                    check = True
                                    count = 1
                                    existingList = existingMetadataFieldInfo.keys()
                                    while check:
                                        if (fieldName + " (Duplicate-" + str(count) + ")") not in existingList:
                                            check = False
                                    fieldNameDesignation = fieldName + " (Duplicate #" + str(count) + ")"

                                existingMetadataFieldInfo[fieldNameDesignation] = {"Description":"", "Source":"", "True Name": "", "Domain":None}
                                if fieldName:
                                    #Add Description if exists
                                    fieldDescription = attr.find("attrdef")
                                    if fieldDescription is not None:
                                        existingMetadataFieldInfo[fieldNameDesignation]["Description"] = fieldDescription.text
                                    #Add Source if exists
                                    fieldSource = attr.find("attrdefs")
                                    if fieldSource is not None:
                                        existingMetadataFieldInfo[fieldNameDesignation]["Source"] = fieldSource.text
                                    
                                    #Add "True Name" for displaying lowercase version of the name (Needed for ones that don't have a corresponding real field to find the lowecase version of)
                                    if fieldNameDesignation == fieldName.upper():
                                        existingMetadataFieldInfo[fieldNameDesignation]["True Name"] = fieldName
                                    else:
                                        existingMetadataFieldInfo[fieldNameDesignation]["True Name"] = fieldNameDesignation
                                uMDNames.append(fieldNameDesignation)
                                
                
                #Find which fields do/don't have metadata
                fieldOptions = []
                missingFields = []
                missingFieldsList = []
                for field in fields:
                    uName = field.name.upper()
                    alias = field.aliasName
                    fieldDesignation = field.name
                    if alias != field.name:
                        fieldDesignation = field.name + " (" + alias + ")"
                    if uName in uMDNames:
                        fieldMDInfo = existingMetadataFieldInfo[uName]
                        fieldOptions.append([fieldDesignation, fieldMDInfo["Description"]])
                        uMDNames.remove(uName)
                    else:
                        missingFields.append([fieldDesignation, ""])
                        missingFieldsList.append([fieldDesignation])

                #Add Field Desc Options parameter
                if fieldOptions:
                    parameters[MDFieldParamIndex].value = fieldOptions
                    parameters[MDFieldParamIndex].enabled = True
                else:
                    parameters[MDFieldParamIndex].enabled = False
                
                #Add metadata without fields parameter
                if uMDNames:
                    param2List = []
                    for MDName in uMDNames:
                        param2List.append([existingMetadataFieldInfo[MDName]["True Name"], existingMetadataFieldInfo[MDName]["Description"], " ", False])
                    parameters[MDWithoutFieldParamIndex].value = param2List
                    parameters[MDWithoutFieldParamIndex].enabled = True
                else:
                    parameters[MDWithoutFieldParamIndex].enabled = False
                
                #Add Fields without metadata parameter
                if missingFieldsList:
                    parameters[MissingFieldsParamIndex].value = missingFields
                    parameters[MissingFieldsListParamIndex].value = missingFieldsList
                    parameters[MissingFieldsParamIndex].enabled = True
                    #Add the filter of potential renaming values to the "Metadata Without Fields"
                    missingFieldFilter = [item[0] for item in missingFieldsList]
                    parameters[MDWithoutFieldParamIndex].filters[2].list = [" "] + missingFieldFilter
                else:
                    parameters[MissingFieldsParamIndex].enabled = False
            
            #Remove "Fields without metadata" if they have metadata being renamed to that field
            if parameters[MDWithoutFieldParamIndex].value:
                missingFieldsList = [item[0] for item in parameters[MissingFieldsListParamIndex].value]
                for values in parameters[MDWithoutFieldParamIndex].value:
                    if values[2] != " ":
                        if values[2] in missingFieldsList:
                            missingFieldsList.remove(values[2])
                existingMissingFieldParams = [item[0] for item in parameters[MissingFieldsParamIndex].value]
                missingFieldParams = []
                for fieldDesignation in missingFieldsList:
                    if fieldDesignation in existingMissingFieldParams:
                        missingFieldParams.append(parameters[MissingFieldsParamIndex].value[existingMissingFieldParams.index(fieldDesignation)]) #Get the existing parameter row so as to not override any parameter settings we dont need to
                    else:
                        missingFieldParams.append([fieldDesignation, ""])
                parameters[MissingFieldsParamIndex].value = missingFieldParams

        else:
            parameters[MDFieldParamIndex].enabled = False
            parameters[MDWithoutFieldParamIndex].enabled = False
            parameters[MissingFieldsParamIndex].enabled = False

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        fcBase = parameters[0].valueAsText
        fc = arcpy.da.Describe(fcBase)['catalogPath']
        MDFieldDescriptions = parameters[MDFieldParamIndex].value
        MDWithoutFields = parameters[MDWithoutFieldParamIndex].value
        MissingFields = parameters[MissingFieldsParamIndex].value

        #Checking which fields to delete from metadata
        msg('... Deleting fields marked for deletion...')
        deleteList = {}
        for row in MDWithoutFields:
            if row[3] == True:
                if "(Duplicate #" in row[0]:
                    dupeNum = int(row[0].split("#")[-1][:-1])
                    if row[0] not in deleteList.keys():
                        deleteList[row[0]] = [dupeNum]
                    else:
                        deleteList[row[0]].append(dupeNum)

                else:
                    DeleteFieldFromMD(fc, row[0].split(" ")[0])

            elif row[2] != " ":
                RenameFieldMetadata(fc, row[0].split(" ")[0], row[2].split(" ")[0])
        
        if len(deleteList.keys()) > 0:
            for key in list(deleteList.keys()):
                DeleteDuplicateFieldsFromMD(fc, key.split(" ")[0], deleteList[key])


        #Add field descriptions
        fieldDescriptionDict = {}

        for row in MDFieldDescriptions:
            fieldDescriptionDict[row[0].split(" ")[0].upper()] = row[1]

        msg('... Adding missing Fields...')
        for row in MissingFields:
            AddFieldToMD(fc, row[0].split(" ")[0].upper())
            fieldDescriptionDict[row[0].split(" ")[0].upper()] = row[1]
        
        msg('... Fixing field metadata descriptions...')
        FixFieldMDDescsEtc(fc, fieldDescriptionDict)

        msg('... Fixing field metadata formatting...')
        FixFieldMDCapitalization(fc)
        FixFieldMDOrder(fc)

        msg('... Synchronizing Metadata...')
        SynchronizeMetadata(fc)

        msg('... Tool complete ...')
        
        return

class FixMetadataDomains(object):
    def __init__(self):
        """This tool checks and fixes Domains within metadata."""
        self.label = "Fix Domains in Metadata"
        self.description = "This tool checks and fixes Domains within metadata"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        fc = arcpy.Parameter(
                displayName = "Destination Feature Class",
                name = "fc",
                datatype = "GPTableView",
                parameterType = "Required",
                direction = "Input")

        domainOptions = arcpy.Parameter(
                displayName = "Metadata Domain Options",
                name = "DomainOptions",
                datatype = "GPString",
                parameterType = "Optional",
                direction = "Input",
                multiValue=True
        )

        rangeDomainOptions = arcpy.Parameter(
                displayName = "Metadata Range Domains",
                name = "RangeDomainOptions",
                datatype = "GPString",
                parameterType = "Optional",
                direction = "Input",
                multiValue=True
        )
        domainOptions.columns = [["GPString", "Field", "READONLY"], ["GPString", "Domain Name", "READONLY"], ["GPString", "Sample Domain Values", "READONLY"], ["Boolean", "Use separate values"], ["Boolean", "Use list of keys"], ["Boolean", "Use list of keys + values"]]
        domainOptions.enabled = False
        rangeDomainOptions.columns = [["GPString", "Field", "READONLY"], ["GPString", "Domain Name", "READONLY"], ["GPString", "Range", "READONLY"]] #["GPString", "Min Value"], ["GPString", "Max Value"]]
        rangeDomainOptions.enabled = False
        # domainValues.columns = [["GPString", "Domain that needs description", "READONLY"], ["GPString", "New Description value"]]
        # domainValues.enabled = False
        
        params = [fc, domainOptions, rangeDomainOptions]#, arcpy.Parameter(
                # displayName = "Test String",
                # name = "String",
                # datatype = "GPString",
                # parameterType = "Optional",
                # direction = "Input")]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        EmptyFieldParam = ["", ""]

        if parameters[0].valueAsText:
            fcBase = parameters[0].valueAsText
            fc = arcpy.da.Describe(fcBase)['catalogPath']

            fields = [field for field in arcpy.ListFields(fc)]
            # domainFields = [field.name for field in fields if field.domain]
            upperDomainFields = [field.name.upper() for field in fields if field.domain]
            # fieldAliases = {field.name.upper():field.aliasName for field in fields if field.domain}
            upperDomainNames = {field.name.upper():field.domain.upper() for field in fields if field.domain}
            
            allDomains = arcpy.da.ListDomains(getWorkspace(fc))
            relevantDomains = [domain for domain in allDomains if domain.name.upper() in upperDomainNames.values()]
            relevantDomainNamesUpper = [domain.name.upper() for domain in relevantDomains]

            if not parameters[0].hasBeenValidated:
                parameters[1].enabled = True

                #Create var to store info  to be used in param updating
                existingMetadataFieldInfo = {field.name.upper():{"Description":"", "Source":"", "Domain":None} for field in fields}

                #Get existing infomation within metadata
                fc_md = arcpy.metadata.Metadata(fc)
                fc_tree = ET.fromstring(fc_md.xml)

                eainfoTree = fc_tree.find("eainfo")
                if eainfoTree is not None:
                    treeDetailed = eainfoTree.find("detailed")
                    if treeDetailed is not None:
                        fieldMetadataList = treeDetailed.findall("attr") #Get the list of fields
                        if fieldMetadataList:
                            for attr in fieldMetadataList:
                                fieldName = attr.findtext("attrlabl")
                                if fieldName:
                                    #Check if there is a domain for the field
                                    if fieldName.upper() in upperDomainFields:
                                        attrdomvs = attr.findall("attrdomv")
                                        if attrdomvs:
                                            #Get the info about hte domain within the metadata
                                            domainInfo = {"Name": "", "Source": "", "ValueList": "", "Values": [], "Range": (None, None)}
                                            for attrdomv in attrdomvs:
                                                if attrdomv.find("codesetd") is not None: #attrdomv with Domain description/Source
                                                    codesetd = attrdomv.find("codesetd")

                                                    codesetn = codesetd.find("codesetn")
                                                    if codesetn is not None:
                                                        domainInfo["Name"] = codesetn.text
                                                    codesets = codesetd.find("codesets")
                                                    if codesets is not None:
                                                        domainInfo["Source"] = codesets.text
                                                elif attrdomv.find("edom") is not None: #attrdomv with Multiple unique values
                                                    edoms = attrdomv.findall("edom")
                                                    for edom in edoms:
                                                        domainValueInfo = {"Value":"", "Value Description":"", "Value Source":""}

                                                        if edom.find("edomv") is not None:
                                                            domainValueInfo["Value"] = edom.find("edomv").text
                                                        if edom.find("edomvd") is not None:
                                                            domainValueInfo["Value Description"] = edom.find("edomvd").text
                                                        if edom.find("edomvds") is not None:
                                                            domainValueInfo["Value Source"] = edom.find("edomvds").text

                                                        domainInfo["Values"].append(domainValueInfo)
                                                elif attrdomv.find("udom") is not None: #attrdomv with List of values
                                                    udom = attrdomv.find("udom")
                                                    domainInfo["ValueList"] = udom.text
                                                elif attrdomv.find("rdom") is not None: #attrdomv with range domain
                                                    rdom = attrdomv.find("rdom")
                                                    rdomin = rdom.find("rdomin")
                                                    rdomax = rdom.find("rdomax")
                                                    domainInfo["Range"] = (rdomin, rdomax)
                                                else:
                                                    pass#?
                                            existingMetadataFieldInfo[fieldName.upper()]["Domain"] = domainInfo
                
                realFieldDomainInfo = {field.name.upper():relevantDomains[relevantDomainNamesUpper.index(upperDomainNames[field.name.upper()])] for field in fields if field.domain}
                
                #Set up parameters
                domainOptions = []
                rangeDomainOptions = []
                testStr = ""
                for field in fields:
                    #Get real field info
                    uName = field.name.upper()
                    alias = field.aliasName
                    fieldDesignation = field.name
                    if alias != field.name:
                        fieldDesignation = field.name + " (" + alias + ")"
                    fieldMDInfo = existingMetadataFieldInfo[uName]
                    #Deal with real domain info
                    if uName in realFieldDomainInfo.keys():
                        realDomainInfo = realFieldDomainInfo[uName]
                        domainMDInfo = None
                        if fieldMDInfo:
                            domainMDInfo = fieldMDInfo["Domain"]

                        #Get the domain name
                        domainNameStr = ""
                        if domainMDInfo and realDomainInfo.name != domainMDInfo["Name"]:
                            domainNameStr = str(domainMDInfo["Name"])+" -> "+str(realDomainInfo.name)
                        else:
                            domainNameStr = str(realDomainInfo.name)
                        
                        #Get sample Values
                        if realDomainInfo.domainType == "CodedValue": #Get values of Coded Values Domain
                            key1 = list(realDomainInfo.codedValues.keys())[0] 
                            key2 = list(realDomainInfo.codedValues.keys())[1]

                            #Get sample values of the domain
                            sampleValueStr = ""
                            if key1 != realDomainInfo.codedValues[key1]:
                                sampleValueStr += "("+str(key1) +" | "+str(realDomainInfo.codedValues[key1])+")"
                            else:
                                sampleValueStr += str(key1)
                            sampleValueStr += "; "
                            if key2 != realDomainInfo.codedValues[key2]:
                                sampleValueStr +=  "(" + str(key2) + " | "+str(realDomainInfo.codedValues[key2])+")"
                            else:
                                sampleValueStr += str(key2)
                            
                            domainOptions.append([fieldDesignation, domainNameStr, sampleValueStr, False, False, False])
                        else: #Get range of Range Domain
                            range = realDomainInfo.range
                            rangeDomainOptions.append([fieldDesignation, domainNameStr, str(range)])

                        #Set the checkmark value in the parameter
                        if uName in list(existingMetadataFieldInfo.keys()): 
                            if domainMDInfo:
                                if realDomainInfo.domainType == "CodedValue": #Coded Values Domain
                                    if domainMDInfo["Values"]: #Exists a separated values list
                                        domainOptions[-1][3] = True #Set "Use separate values" to true
                                    elif domainMDInfo["ValueList"]: #Exists a value list
                                        valueList = domainMDInfo["ValueList"]
                                    
                                        firstValueInList = valueList.split(";")[0]
                                        if firstValueInList in list(realDomainInfo.codedValues.keys()) or firstValueInList.split(" (default)")[0] in list(realDomainInfo.codedValues.keys()):
                                            domainOptions[-1][4] = True
                                        elif firstValueInList.split(" | ")[0] in list(realDomainInfo.codedValues.keys()):
                                            domainOptions[-1][5] = True
                                    elif domainMDInfo["Range"] != (None, None): #in the metadata there is a range from some reason?
                                        pass
                                else: #Range Domain (no checkmarks)
                                    if domainMDInfo["Range"]:
                                        pass
                                    elif domainMDInfo["Values"]:
                                        pass
                                    elif domainMDInfo["ValueList"]:
                                        pass
                #Show parameters if there are values, otherwise hide
                if domainOptions:
                    parameters[1].value = domainOptions
                    parameters[1].enabled = True
                else:
                    parameters[1].enabled = False
                if rangeDomainOptions:
                    parameters[2].value = rangeDomainOptions
                    parameters[2].enabled = True
                else:
                    parameters[2].enabled = False
                # parameters[-1].value = "invalidated"
            else:
                # parameters[-1].value = "validated"
                pass
            #Set up domainValueOptions param
            # parameters[2].enabled = False
            # domainValueOptions = []
            # testStr = ""
            # if parameters[1].value:
            #     for fieldParam in parameters[1].value:
            #         if fieldParam[3]:
            #             domainName = fieldParam[1]
            #             if " -> " in domainName:
            #                 domainName = domainName.split(" -> ")[1]
            #             relevantDomains[relevantDomainNamesUpper.index(domainName)]
            #             testStr += str(domainName) + " | "
            #     parameters[2].value = domainValueOptions
            # else:
            #     parameters[1].enabled = False
        else:
            parameters[1].enabled = False
            parameters[2].enabled = False
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        fcBase = parameters[0].valueAsText
        fc = arcpy.da.Describe(fcBase)['catalogPath']
        MDDomainOptions = parameters[1].value
        MDRangeDomainOptions = parameters[2].value

        

        # get the gdb where the fc lives
        gdb = getWorkspace(fc)

        fc_name = fc.split("\\")[-1]

        msg('... ensuring domains were added to metadata...')

        valueDescriptions = {}

        if MDDomainOptions:
            for domainOptions in MDDomainOptions:
                fieldName = domainOptions[0].split(" ")[0]
                if domainOptions[3]:
                    valueDescriptions[fieldName] = "Use Separate Values"
                elif domainOptions[4]:
                    valueDescriptions[fieldName] = "Use List of Keys"
                elif domainOptions[5]:
                    valueDescriptions[fieldName] = "Use List of Keys/Values"

            # msg(valueDescriptions)
        
        if MDRangeDomainOptions:
            for rangeDomainOption in MDRangeDomainOptions:
                fieldName = rangeDomainOption[0].split(" ")[0]
                valueDescriptions[fieldName] = "Range"
        # msg(valueDescriptions)
        if valueDescriptions:
            AddDomainsToMD(fc, valueDescriptions)

        msg('... Tool complete ...')
        
        return

class CheckMetadataQuality(object):

    def __init__(self):
        self.label = "Check Metadata Quality"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Helper Tools"

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

class ImportMetadata(object):
    def __init__(self):
        self.label = "Import Metadata"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Helper Tools"

    def getParameterInfo(self):
        params = [
            arcpy.Parameter(
            displayName = "Source Metadata Layer",
            name = "Source Feature Class",
            datatype = "GPTableView",
            parameterType = "Required",
            direction = "Input"),

            arcpy.Parameter(
            displayName = "Destination Metadata Layer",
            name = "Destination Feature Class",
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
        fcBase0 = parameters[0].valueAsText
        Sourcefc = arcpy.da.Describe(fcBase0)['catalogPath']
        fcBase1 = parameters[1].valueAsText
        Destinationfc = arcpy.da.Describe(fcBase1)['catalogPath']
        ImportUnsyncedMetadata(Sourcefc, Destinationfc)

class TestingTool(object):
    def __init__(self):
        self.label = "TEST"
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
        addDefaultsToNewField(fc, "UNITCODE", "YOSE")
        return