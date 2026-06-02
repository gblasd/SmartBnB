CREATE TABLE IF NOT EXISTS reviews (
    listing_id NUMERIC(10),
    id NUMERIC(10),
    date DATE,
    reviewer_id NUMERIC(10),
    reviewer_name TEXT,
    comments TEXT,
    año_trimestre NUMERIC(7)
);