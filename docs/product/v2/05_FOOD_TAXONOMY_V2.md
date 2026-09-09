# V2 Food Taxonomy

## Contract

Food taxonomy has exactly two required levels:

- `primary_category`
- `subcategory`

The database and API use the stable keys below. The UI uses the listed Arabic
labels. A subcategory is valid only beneath its listed primary category.

| Primary key | Arabic label | Subcategory keys and Arabic labels |
|---|---|---|
| `grains_and_starches` | الحبوب والنشويات | `rice` الأرز; `oats` الشوفان; `pasta` المعكرونة; `bulgur` البرغل; `jareesh` الجريش; `wheat` القمح; `barley` الشعير; `corn` الذرة; `potatoes` البطاطس; `sweet_potatoes` البطاطا الحلوة; `other` أخرى |
| `bakery` | المخبوزات | `bread` الخبز; `toast` التوست; `samoli` الصامولي; `croissant` الكرواسون; `pastries` المعجنات; `tortilla_and_wraps` التورتيلا واللفائف; `biscuits_and_crackers` البسكويت والمقرمشات; `other` أخرى |
| `meat_and_poultry` | اللحوم والدواجن | `chicken` الدجاج; `turkey` الديك الرومي; `beef` اللحم البقري; `lamb` لحم الغنم; `camel` لحم الإبل; `eggs` البيض; `processed_meat` اللحوم المصنعة; `other` أخرى |
| `fish_and_seafood` | الأسماك والمأكولات البحرية | `fish` الأسماك; `tuna` التونة; `shrimp` الروبيان; `crustaceans` القشريات; `mollusks` الرخويات; `other` أخرى |
| `dairy_products` | الألبان ومنتجاتها | `milk` الحليب; `laban` اللبن; `yogurt` الزبادي; `labneh` اللبنة; `cheese` الأجبان; `cream_and_qishta` القشطة والكريمة; `other` منتجات ألبان أخرى |
| `legumes` | البقوليات | `lentils` العدس; `chickpeas` الحمص; `beans` الفاصوليا; `fava_beans` الفول; `peas` البازلاء; `cowpeas` اللوبيا; `lupin` الترمس; `other` أخرى |
| `vegetables` | الخضروات | `leafy_vegetables` الخضروات الورقية; `cruciferous_vegetables` الخضروات الصليبية; `root_vegetables` الخضروات الجذرية; `tomatoes` الطماطم; `cucumber` الخيار; `peppers` الفلفل; `onion_and_garlic` البصل والثوم; `zucchini_and_squash` الكوسا والقرع; `eggplant` الباذنجان; `mushrooms` الفطر; `other` خضروات أخرى |
| `fruits` | الفواكه | `citrus` الحمضيات; `apples_and_pears` التفاح والكمثرى; `bananas` الموز; `grapes` العنب; `berries` التوت; `stone_fruits` الفواكه ذات النواة; `tropical_fruits` الفواكه الاستوائية; `watermelon_and_melon` البطيخ والشمام; `dates` التمر; `pomegranate` الرمان; `figs` التين; `dried_fruits` الفواكه المجففة; `other` فواكه أخرى |
| `nuts_and_seeds` | المكسرات والبذور | `almonds` اللوز; `walnuts` الجوز; `cashews` الكاجو; `pistachios` الفستق; `hazelnuts` البندق; `peanuts` الفول السوداني; `sesame_seeds` بذور السمسم; `chia_seeds` بذور الشيا; `flax_seeds` بذور الكتان; `sunflower_seeds` بذور دوار الشمس; `pumpkin_seeds` بذور اليقطين; `other` مكسرات وبذور أخرى |
| `fats_and_oils` | الدهون والزيوت | `olive_oil` زيت الزيتون; `vegetable_oils` الزيوت النباتية; `coconut_oil` زيت جوز الهند; `butter` الزبدة; `ghee` السمن; `margarine` السمن النباتي; `other` دهون وزيوت أخرى |
| `sweets_and_sugars` | الحلويات والسكريات | `cake` الكيك; `chocolate` الشوكولاتة; `sweet_biscuits` البسكويت الحلو; `middle_eastern_sweets` الحلويات الشرقية; `western_desserts` الحلويات الغربية; `ice_cream_and_frozen_desserts` الآيس كريم والحلويات المجمدة; `candy` الحلوى والسكاكر; `sugar_and_sweeteners` السكر والمحليات; `jam_and_sweet_spreads` المربى والدهن الحلو; `other` حلويات وسكريات أخرى |
| `beverages` | المشروبات | `water` الماء; `coffee` القهوة; `tea` الشاي; `juices` العصائر; `carbonated_drinks` المشروبات الغازية; `energy_drinks` مشروبات الطاقة; `sports_drinks` المشروبات الرياضية; `plant_based_drinks` المشروبات النباتية; `shakes_and_smoothies` المشروبات المخفوقة; `other` مشروبات أخرى |
| `meals` | الوجبات | `rice_dishes` أطباق الأرز; `pasta_dishes` أطباق المعكرونة; `burgers_and_sandwiches` البرغر والسندويتشات; `shawarma` الشاورما; `pizza` البيتزا; `salads` السلطات; `soups` الشوربات; `main_dishes` الأطباق الرئيسية; `breakfast_meals` وجبات الإفطار; `other` وجبات أخرى |
| `sauces_spices_and_additions` | الصلصات والتوابل والإضافات | `sauces` الصلصات; `mayonnaise` المايونيز; `dressings` التتبيلات; `tahini` الطحينة; `spices_and_seasonings` التوابل والبهارات; `herbs` الأعشاب; `salt` الملح; `vinegar` الخل; `additions` الإضافات; `other` أخرى |
| `other` | أخرى | `other` أخرى |

## Migration fallback

- Known primary and known valid subcategory map deterministically.
- Known primary with an unknown or invalid subcategory maps to that primary and `other`.
- Unknown primary maps to `other` and `other`.

Migration must never infer a more specific classification than the source data
supports. Registry schema version `4` owns the API/UI taxonomy contract.
