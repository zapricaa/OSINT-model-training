-- Initialize Apache AGE extension and create the investigation graph
CREATE EXTENSION IF NOT EXISTS age;

-- Load AGE into the search path
LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- Create the OSINT knowledge graph
SELECT create_graph('osint_graph');
