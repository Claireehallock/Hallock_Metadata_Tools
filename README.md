# DataStandardsWithMetadata
Python Toolbox with tools to add data standard fields from a source dataset to a target dataset, along with metadata.

Process
- attempts to renames fields in target if they share a name with source fields. Will break if an "[fldname]_old" already exists in target.
- creates all fields from source within target except objectid and shape.
- imports metadata related to fields from the source into the target.

Notes
- allows user to populate default values for the fields. The script will not field calculate the attribute, but future records will have default values.
- before running this tool look at the target metadata and syncrhonize it. This will import a framework for the source metadata to land.
