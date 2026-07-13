select l.id, l.listing_url, l.name, l.description, l.neighborhood_overview, l.neighbourhood_cleansed,
        l.property_type, l.room_type, l.accommodates, l.bathrooms, l.bathrooms_text, l.bedrooms, 
        l.beds, l.amenities, l.price, l.latitude, l.longitude, l.minimum_nights, l.maximum_nights, 
        l.has_availability, l.review_scores_accuracy, l.review_scores_communication,
        l.review_scores_cleanliness, l.review_scores_location, l.review_scores_value, 
        l.review_scores_rating, l.reviews_per_month, l.instant_bookable,
        l.calculated_host_listings_count, l.calculated_host_listings_count_entire_homes,
        l.calculated_host_listings_count_private_rooms, l.calculated_host_listings_count_shared_rooms
    from public.listings l
   where l.has_availability is true 
     and l.description is not null
   order by length(l.description) desc
   limit 5