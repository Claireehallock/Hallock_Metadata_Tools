# Hallock_MetadataTools
Python Toolbox created for ArcGIS v3.3, should be compatible with later versions, may or may not be compatible with earlier versions.

## Downloading
To download, you can either download just the [Hallock_MetadataTools.pyt](https://github.com/Claireehallock/Hallock_Metadata_Tools/blob/main/Hallock_MetadataTools.pyt) file, or download the whole set of code and add that toolbox while inside ArcGIS Pro.

## Primary Tools
### Add STANDARD Fields and their Metadata
Adds data standard fields from a source (template) data standards dataset to a target dataset
- If a field already exists with that name, you are given the option to either rename the field or have it be updated to match how the field is set up in the template.
- Does not override any data or metadata in fields found outside of the template.
- Allows selections of defaults for NPS-specific fields such as Region, Group Code, and Unit Code.

### Add Metadata to Existing STANDARD Fields
Transfers field metadata related to data standard fields from a source(template) dataset to a target dataset
- Requires that all the template fields exist in the source 
- Does not overriding existing metadata in other fields

### Fix Fields Metadata
Increases quality and consistency of field metadata
- In metadata, will find fields missing metadata, fields with duplicate metadata, and fields within metadata that don't exist within the layer.
- For fields that don't exist within the layer, the program gives the option of either renaming the field to match a field that doesn't have metadata or deleting it.
- Adds "-" as a placeholder value to sections of metadata that need to be filled in, but cannot be filled in by a computer, to add greater clarity in the metadata of what needs editing.

### Fix Domains in Metadata
Increases quality and consistency of domain metadata
- Checks for which domains do and do not exist in metadata
- Gives options of whether to have "separate values", where each value in the domain has its own section in metadata and a description, or to have a "list", where the values are listed out in text format
- The list can either be just the names of the values in the domain, or the values and their aliases.
- If you choose separate values and there are not existing descriptions to draw from, the alias of the domain value will be used as the default description

## Helper Tools
### Import Metadata
Copies metadata from one layer to another without synchronizing and altering it
- There exists a built-in function called import metadata, but this one does not synchronize the metadata during that. Synchronizing the metadata will fix the layer name within the metadata, but if you are concerned about overriding metadata, synchronization has a chance to do that.

### Check Metadata Quality
Checks the general quality of metadata
- Also checks for placeholders that should be filled in with permanent values.
- Currently is not fully implemented, and primarily only checks field metadata

# Contact
Contact Claire Hallock at CHallock@nps.gov or ClaireEHallock@gmail.com for questions.

Created at YOSE for use by National Park Service Employees, but can be used by others.