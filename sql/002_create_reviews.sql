create table if not exists reviews (
    listing_id numeric(50),
    id numeric(50),
    date date,
    reviewer_id numeric(50),
    reviewer_name text,
    comments text,
    primary key (id)
);