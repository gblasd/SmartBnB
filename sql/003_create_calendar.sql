create table if not exists calendar (
    listing_id numeric(50),
    date date,
    available boolean,
    price numeric(30),
    adjusted_price numeric(30),
    minimum_nights numeric(30),
    maximum_nights numeric(30),
    calendar_updated date,
    
    primary key (listing_id, date)
)