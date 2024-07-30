# Key Entities
1.  Brand
2.  Product
3.  Campaign
4.  Guideline
5.  Market
6.  Competitor
7.  Influencer
8.  Advertising Case
9.  Aesthetic
10. Slogan

# Attributes
•   Brand:
    o   Name
    o   Elements
    o   Target Consumer
    o   Slogan
    o   Color Palette
    o   Logo Usage
    o   Accent Usage
    o   Storyboard Guidelines
    o   Social Media Guidelines

•   Product:
    o   Name
    o   Type (e.g. SaaS, On-Premise)
    o   Popularity
    o   Market (e.g., UK, US)

•   Campaign:
    o   Name
    o   Focus (e.g., Digital Experience, AI)
    o   Market
    o   Creative Assets
    o   Concept
    o   Toolkit

•   Guideline:
    o   Type (e.g., Digital Asset, Tone of Voice Usage, Logo Usage)
    o   Details

•   Market:
    o   Name
    o   Trends
    o   Competitors
    o   Influencers

•   Competitor:
    o   Name
    o   Products
    o   Campaigns

•   Influencer:
    o   Name
    o   Market
    o   Segment (e.g., Coffee, Lifestyle)

•   Advertising Case:
    o   Market
    o   Details

•   Aesthetic:
    o   Style (e.g., Minimalist, Modern)
    o   Target Audience

# Relationships
•   Brand:
    o   "has_product" -> Product
    o   "runs_campaign" -> Campaign
    o   "follows_guideline" -> Guideline
    o   "targets_market" -> Market
    o   "competes_with" -> Competitor
    o   "collaborates_with" -> Influencer
    o   "featured_in_advertising_case" -> Advertising Case
•   Product:
    o   "belongs_to_brand" -> Brand
    o   "popular_in_market" -> Market
    o   "competes_with" -> Competitor
    o   "follows_guideline" -> Guideline
•   Campaign:
    o   "belongs_to_brand" -> Brand
    o   "targets_market" -> Market
    o   "uses_guideline" -> Guideline
    o   "includes_toolkit" -> Toolkit

•   Guideline:
    o   "applies_to_brand" -> Brand
    o   "applies_to_product" -> Product
    o   "applies_to_campaign" -> Campaign
•   Market:
    o   "includes_product" -> Product
    o   "includes_competitor" -> Competitor
    o   "includes_influencer" -> Influencer

•   Competitor:
    o   "competes_with_brand" -> Brand
    o   "competes_with_product" -> Product

•   Influencer:
    o   "collaborates_with_brand" -> Brand
•   Recipe:
    o   "belongs_to_product" -> Product
    o   "follows_aesthetic" -> Aesthetic
•   Translation:
    o   "used_by_brand" -> Brand
•   Advertising Case:
    o   "features_brand" -> Brand
•   Sustainability Claim:
    o   "promoted_by_brand" -> Brand
