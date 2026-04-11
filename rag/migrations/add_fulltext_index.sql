-- Add tsvector column for full-text search
ALTER TABLE document_chunks
ADD COLUMN IF NOT EXISTS text_search tsvector
GENERATED ALWAYS AS (to_tsvector('english', text)) STORED;

-- Create GIN index for fast full-text search
CREATE INDEX IF NOT EXISTS chunks_fulltext_idx
ON document_chunks USING gin(text_search);