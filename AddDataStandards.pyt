# -*- coding: utf-8 -*-

import arcpy
import sys

def msg(txt):
    print(txt)
    arcpy.AddMessage(txt)

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Add Data Standards + Metadata"
        self.alias = "Add Data Standards + Metadata"

        # List of tool classes associated with this toolbox
        self.tools = [AddDataStandardsToExistingFC, JustAddMetadata]


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
                datatype = "DEFeatureClass",
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
        
        params = [fc, template, default_unit_code, default_unit_name, default_group_code, default_group_name, default_region_code]
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
        fc = parameters[0].valueAsText
        template = parameters[1].valueAsText
        unit_code = parameters[2].valueAsText
        unit_name = parameters[3].valueAsText
        group_code = parameters[4].valueAsText
        group_name = parameters[5].valueAsText
        region_code = parameters[6].valueAsText

        # get the gdb where the fc lives
        gdb = '\\'.join(fc.split('\\')[0:-1])

        msg('... Making backup copy of original feature class ...')

        fc_name = fc.split("\\")[-1]
        backup_fc_name = f"{fc_name}_original"

        # let user know backup copy already exists
        if arcpy.Exists(f"{gdb}\{backup_fc_name}"):
            msg(f" -- {backup_fc_name} already exists in {gdb} --")
            msg(" -- not creating a backup --")

        # create backup
        else:
            if '_tbl' in backup_fc_name: arcpy.conversion.TableToTable(fc, gdb, backup_fc_name)
            else: arcpy.conversion.FeatureClassToFeatureClass(fc, gdb, backup_fc_name)


        msg(f'... Rename data standard fields that already exist in {fc_name} ...')

        # compare fields, find similar
        FCfield_names = [f.name.upper() for f in arcpy.ListFields(fc)] 
        STfield_names = [f.name.upper() for f in arcpy.ListFields(template)]
        MatchField_Names = list(set(FCfield_names).intersection(set(STfield_names)))

        msg('... Renaming existing fields...')
        for fld in MatchField_Names:
            arcpy.management.AlterField(fc, fld, f"{fld}_old")

        # get domains in template gdb
        template_gdb = '\\'.join(template.split('\\')[0:-1])
        template_doms = {dom.name: dom for dom in arcpy.da.ListDomains(template_gdb)}

        # adding fields!
        msg('... Adding data standards ...')

        # domains already in fc gdb
        doms = [dom.name for dom in arcpy.da.ListDomains(gdb)]

        for fld in arcpy.ListFields(template):

            # don't add objectid or shape fields
            if fld.name in ['OBJECTID', 'Shape']: continue

            msg(f' - {fld.name}')

            # handle domains
            if fld.domain != '':

                # if domain has not been added to gdb yet
                if fld.domain not in doms:
                    dom = template_doms[fld.domain]

                    # parse domain inputs
                    domType = 'CODED' if dom.domainType == 'CodedValue' else 'Range'

                    if dom.splitPolicy == 'DefaultValue': domSP = 'DEFAULT'
                    elif dom.splitPolicy == 'Duplicate': domSP = 'DUPLICATE'
                    else: domSP = 'GEOMETRY'

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

        # get existing metadata from fc and template
        fc_md = arcpy.metadata.Metadata(fc)
        template_md = arcpy.metadata.Metadata(template)

        # extract template field metadata
        template_xml = template_md.xml
        start_tag = '<attr xmlns="">'
        end_tag = '</detailed>'
        template_txt = template_xml.split(start_tag, 1)[1].split(end_tag)[0]

        # insert template txt into original metadata
        fc_xml = fc_md.xml
        fc_xml_list = fc_xml.split(end_tag)

        new_xml = start_tag.join([fc_xml_list[0], template_txt])
        new_xml = end_tag.join([new_xml, fc_xml_list[1]])

         # save xml
        fc_md.xml = new_xml

        best_md = arcpy.metadata.Metadata(fc)
        best_md.copy(fc_md)
        best_md.save()

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
                datatype = "DEFeatureClass",
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
        
        fc = parameters[0].valueAsText
        template = parameters[1].valueAsText
        gdb = '\\'.join(fc.split('\\')[0:-1])

        msg('... Adding field metadata ...')

        # get existing metadata from fc and template
        fc_md = arcpy.metadata.Metadata(fc)
        template_md = arcpy.metadata.Metadata(template)

        # extract template field metadata
        template_xml = template_md.xml
        start_tag = '<attr xmlns="">'
        end_tag = '</detailed>'
        template_txt = template_xml.split(start_tag, 1)[1].split(end_tag)[0]

        # insert template txt into original metadata
        fc_xml = fc_md.xml
        fc_xml_list = fc_xml.split(end_tag)

        new_xml = start_tag.join([fc_xml_list[0], template_txt])
        new_xml = end_tag.join([new_xml, fc_xml_list[1]])

         # save xml
        fc_md.xml = new_xml

        best_md = arcpy.metadata.Metadata(fc)
        best_md.copy(fc_md)
        best_md.save()

        msg('... Tool complete ...')
        
        return
