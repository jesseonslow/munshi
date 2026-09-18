# 1. Feed directly into your NER sweep / lookup cache
entities = [
    "Malaysian Branch of the Royal Asiatic Society",
    "Journal of the Malaysian Branch of the Royal Asiatic Society",
    "Sultan Abdul Ghafur Muhiuddin Shah",
    "Sultan Abdul Jalil Shah III",
    "Abdul Rahman ibni al-Marhum Tuanku Mohamed Shah",
    "Tunku Abdul Rahman",
    "Sultan Abdul Samad",
    "Munshi Abdullah",
    "Dato' Abdullah bin Ali",
    "Sultan Abu Bakar",
    "Abu Talib Ahmad",
    "Aceh",
    "Agriculture",
    "Nik Ahmad Kamil",
    "Sheikh Ahmad Majani",
    "Ahmad Shah ibn Iskander",
    "Sultan Ala'u'd-din Ri'ayat Shah",
    "Syed Hussein Alatas",
    "Alexander the Great",
    "Raja Ali Haji",
    "Charles Allen",
    "Alphabet",
    "Amok",
    "Amulets",
    "Anglo-Burmese War",
    "Animals",
    "Antiquities",
    "Anthropology",
    "Physical anthropology",
    "Social anthropology",
    "Ants",
    "Apes",
    "Archaeology",
    "Archery",
    "Architecture",
    "Archives",
    "Armenians",
    "Arms and armour",
    "Art",
    "Babas",
    "Sultan Badlishah",
    "Dr. Badriyah Haji Salleh",
    "Bagan (Johor)",
    "Bajau",
    "Banks and banking",
    "Ban Hin Lee Bank",
    "Joseph Alexander Bannerman",
    "Joseph Balestier",
    "Baptist Mission Press",
    "Duarte Barbosa",
    "Warren Delabere Barnes",
    "Basel Mission in North Borneo",
    "Baskets",
    "David Kenneth Bassett",
    "Bataks",
    "Bats",
    "Jean Chretian Baud",
    "Beads",
    "Odoardo Beccari",
    "Bees",
    "Beetles",
    "Begonias",
    "Harry Jindřich Benda",
    "Francis James Bernard",
    "Isabella Bird",
    "Birds",
    "Charles Otto Blagden",
    "Edward Blundell",
    "Boats",
    "Borneo",
    "Borobudur",
    "Raja Bot bin Raja Jumaat",
    "Botanists and botanical gardens",
    "Botany",
    "Dato' Sir Roland St. John Braddell",
    "Renward Brandstetter",
    "Brass-founding",
    "Brinjal",
    "Britain in Malaya and Borneo",
    "Britain in Southeast Asia",
    "British North Borneo",
    "Bronzes",
    "James Brook",
    "Charles Brook",
    "Charles Vyner Brooke",
    "Brunei",
    "Buddha",
    "Buddhism",
    "Bugis",
    "Bulbuls",
    "Bulls",
    "Bull-fights",
    "Burma",
    "Butterflies",
    "Calculi",
    "Calendar",
    "Cambodia",
    "Cambridge University Expedition",
    "Cameron Highlands",
    "Camphor tree",
    "Cannon",
    "Cardinal points",
    "Cards",
    "Cartography",
    "Cattle",
    "Caves",
    "Celebes",
    "Centipeddes",
    "Ceramics",
    "Cercopidae",
    "Chams",
    "Chan Wing",
    "Charms",
    "Cheah Boon Kheng",
    "Cheng Ho",
    "Chinese in Malaysia",
    "Chinese in Singapore",
    "Chinese language",
    "Chinese literature",
    "Christianity",
    "Christmas Island",
    "Churches",
    "Cirripedia",
    "Colonial Civil Service",
    "Sir Hugh Charles Clifford",
    "Coal",
    "Cockatoos",
    "Cockroaches",
    "Cocoa",
    "Coconut",
    "Coconut palms",
    "Cocos-Keeling Islands",
    "Coffee",
    "Coins",
    "Communism",
    "Contract labour",
    "Cooperative societies",
    "Edred John Henry Corner",
    "Gaspar Correa",
    "Abraham Couperus",
    "Crabs",
    "John Crawfurd",
    "Crimes and criminals"
    "Coronations",
    "Crocodiles",
    "Carlos Cuarteron",
    "Currency",
    "Customary law",
    "Dancing",
    "Dayak language",
    "Dayaks",
    "Decoration and ornament",
    "Deer",
    "Nicholas Belfield Dennys",
    "Dermaptera",
    "Tunku Dhiauddin ibn Sultan Zainal Rashid I",
    "Dialects and dictionaries",
    "Diamonds",
    "Dipterocarpaceae",
    "Divination",
    "Divorce",
    "Jakarta",
    "Djalan Sampoerna",
    "Dogs",
    "Dragonflies",
    "William Bloomfield Douglas",
    "Joseph Ducroix",
    "Robert William Duff",
    "Dusuns",
    "Bronze drums",
    "Dutch in Borneo",
    "Dutch in Indonesia",
    "Dutch in Malaya",
    "Dutch East India Company",
    "Dyes and dyeing",
    "George Windsor Earl",
    "Earthquakes",
    "East India Company",
    "Education",
    "Egypt",
    "Elephants",
    "John Minor Echols",
    "Environment",
    "Manuel Godinho de Erédia",
    "Ethnography",
    "Malay etiquette",
    "Ivor Hugh Norman Evans",
    "Exorcism",
    "Explorers",
    "Falcons",
    "Hamzah Fansuri",
    "Sir Robert Townsend Farquhar",
    "J. W. Farren",
    "Fasts and feasts",
    "Ferns",
    "Fertilisation",
    "Festivals",
    "Fire",
    "Fish",
    "Fisheries",
    "Flags",
    "Flies",
    "Flight",
    "Flint",
    "Floods",
    "Flowers",
    "Folklore",
    "Forests and forestry",
    "Formosa",
    "Thomas Forrest",
    "France and the French",
    "Federated Malay States",
    "Fraser's Hill",
    "Frogs",
    "Fruit",
    "Funeral rites and ceremonies",
    "Furniture",
    "Paulo da Gama",
    "Gambling",
    "Gamelan",
    "Gantang",
    "Geology",
    "Geopolitics",
    "Germany",
    "Gibbons",
    "Carl Alexander Gibson-Hill",
    "John Desmond Gimlette",
    "Ginger",
    "Goats",
    "Gold mines",
    "Gold artefacts",
    "Sir Lawrence Nunns Guillemard",
    "John Michael Gullick",
    "Gulls",
    "Gums and resins",
    "Gutta-percha",
    "Gymnosperms",
    "Abraham Hale",
    "James Hatton Hall",
    "Hang Tuah",
    "Hang Jebat",
    "Alexander Hare",
    "Joanna Hare",
    "Tom Harrisson",
    "Hats",
    "Frank Hatton",
    "Hawks",
    "Herbs",
    "Heritage and conservation",
    "Dudley Francis Amelius Hervey".
    "Heteroptera",
    "Anthony Haydock Hill",
    "Homoptera",
    "Christian Hooykaas",
    "Hornbills",
    "Bishop George Frederick Hose",
    "Hospitals",
    "Houses and shophouses",
    "Hsieh Ching-Kao",
    "Hsu Yun Tsaio",
    "Hunting and trapping",
    "Hymenoptera",
    "Hysteria",
    "Ibans"
    "Sultan Ibrahim ibni Sultan Abu Bakar",
    "Idols and images",
    "Illanuns",
    "Inas",
    "Incantations",
    "Incense burners",
    "Indians",
    "Indo-China",
    "Indonesia",
    "Indonesians in Malaya",
    "Inheritance",
    "Emily Innes",
    "Inscriptions",
    "Insects"
    "Iran",
    "Iron age",
    "Sultan Iskander Shah",
    "Islam",
    "Islands",
    "Ismail Abdul Rahman",
    "Jade",
    "Jakun",
    "Japan",
    "Java",
    "Jawi alphabet",
    "Jelubu",
    "Johor",
    "Johor Lama",
    "Journal of the Indian Archipelago",
    "Kampong Banggul Ara",
    "Kampong Ipoh",
    "Kangchu System",
    "Karimun Islands",
    "Katydids",
    "Kedah",
    "Kelabits",
    "Kelantan",
    "Henry Robert Kelham",
    "Kenyah",
    "Keppel Harbour",
    "Keramat",
    "Kerinchi",
    "Keris",
]

# 2. Key-value mapping for fast alias lookups
aliases = {
    "Malaysian Branch of the Royal Asiatic Society": [
        "MBRAS",
        "Malayan Branch of the Royal Asiatic Society",
        "Straits Branch of the Royal Asiatic Society",
        "SBRAS"
    ],
    "Journal of the Malaysian Branch of the Royal Asiatic Society": [
        "JMBRAS",
        "JSBRAS",
        "Journal of the Malayan Branch of the Royal Asiatic Society",
        "Journal of the Straits Branch of the Royal Asiatic Society"
    ]
    "Abd al-Ghafur Muhaiyu'din Shah, Sultan of Pahang": [
        "Abd al-Ghafur Muhaiyu'din Shah, Sultan of Pahang, r.1592-1614",
        "Abd al-Ghafur Muhaiyu'din Shah",
        "Sultan of Pahang Abd al-Ghafur",
        "Sultan Abd al-Ghafur",
        "Abd al-Ghafur Muhaiyu'din Shah, Sultan of Pahang"
    ],
    "Abdul Jalil Riayat Shah III, Sultan of Johor": [
        "Abdul Jalil Riayat Shah III",
        "Sultan of Johor Abdul Jalil Riayat Shah III",
        "Sultan Abdul Jalil Riayat Shah III",
        "Abdul Jalil Riayat Shah III, Sultan of Johor",
        "Abdul Jalil Shah III of Johor"
    ],
    "Abdul Rahman ibni al-Marhum Tuanku Mohamed Shah": [
        "Abdul Rahman ibni al-Marhum Tuanku Mohamed Shah, Tuanku, 1895-1960",
        "Tuanku Abdul Rahman",
        "Abdul Rahman of Negeri Sembilan"
    ],
    "Tunku Abdul Rahman": [
        "Abdul Rahman",
        "Abdul Rahman Putra",
        "Tunku Abdul Rahman",
        "Tunku Abdul Rahman Putra"
    ],
    "Sultan Abdul Samad": [
        "Abdul Samad",
        "Abdul Samad of Selangor",
        "Raja Abdul Samad",
        "Abdool Shamat",
        "Abdul Shamat",
        "Abdool Shamad",
        "Sultan Abdul Samad of Selangor"
    ],
    "Munshi Abdullah": [
        "Abdullah bin Abdul Kadir",
        "Munshi Abdullah bin Abdul Kadir"
    ],
    "Dato' Abdullah bin Ali": [
        "Abdullah bin Ali"
    ],
    "Sultan Abu Bakar": [
        "Albert Baker",
        "Sultan Abu Bakar of Johor",
        "Abu Bakar of Johor",
        "Temenggong Abu Bakar",
        "Maharaja Abu Bakar"
    ],
    "Nik Ahmad Kamil": [
        "Nik Ahmad Kamil bin Nik Mahmud",
        "Tan Sri Dato' Nik"
    ],
    "Sheikh Ahmad Majani": [
        "Ahmad Majani"
    ],
    "Ahmad Shah ibn Iskander": [
        "Ahmad Shah"
    ],
    "Sultan Ala'u'd-din Ri'ayat Shah": [
        "Ala'u'd-din Ri'ayat Shah",
        "Alauddin Riayat Shah"
    ],
    "Syed Hussein Alatas": [
        "Syed Hussein bin Syed Ali Alatas",
        "Alatas, Syed Hussein",
        "Alatas, S. H.",
        "Alatas, Hussein, Syed"
    ],
    "Raja Ali Haji": [
        "Raja Ali Haji bin Raja Haji Ahmad"
    ],
    "Charles Allen": [
        "Allen, Charles"
    ],
    "Amok": [
        "Amuck"
    ],
    "Anglo-Burmese War": [
        "Anglo-Burmese War, 1824",
        "1824 Anglo-Burmese War"
    ],
    "Sultan Badlishah": [
        "Badlishah",
        "K. Tunku Badlishah"
    ],
    "Dr. Badriyah Haji Salleh": [
        "Badriyaj Haji Salleh",
        "Dr Badriyah Haji Salleh"
    ],
    "Bagan (Johor)": [
        "Bagan"
    ],
    "Joseph Alexander Bannerman": [
        "Bannerman, J. A.",
        "J. A. Bannerman"
    ],
    "Baptist Mission Press": [
        "Sumatran Mission Press",
        "Baptist Mission Press at Bencoolen"
    ],
    "Basel Mission in North Borneo": [
        "Basel Mission"
    ],
    "Jean Chretian Baud": [
        "J.C. Baud",
        "J. C. Baud"
    ],
    "Harry Jindřich Benda": [
        "Harry Jindrich Benda"
    ],
    "Charles Otto Blagden": [
        "C. O. Blagden"
    ],
    "Edward Blundell": [
        "Governor Blundell"
    ],
    "Raja Bot bin Raja Jumaat": [
        "Raja Bot"
    ],
    "Botanists and botanical gardens": [
        "Botanists",
        "Botanical gardens"
    ],
    "Dato' Sir Roland St. John Braddell": [
        "Sir Roland St. John Braddell",
        "Roland Braddell"
    ],
    "James Brooke": [
        "Sir James Brooke",
        "Raja James Brooke",
        "Raja Brooke"
    ],
    "Charles Brooke": [
        "Sir Charles Anthoni Johnson Brooke",
        "Charles Anthoni Johnson",
        "Sir Charles Brooke"
    ],
    "Charles Vyner Brooke": [
        "Sir Charles Vyner Brooke",
        "Sir Charles Vyner de Windt Brooke"
    ],
    "Cheah Boon Kheng": [
        "Dr. Cheah Boon Kheng",
        "Dr Cheah Boon Kheng"
    ],
    "Cheng Ho": [
        "Admiral Cheng Ho",
        "Admiral Ho"
    ],
    "Negeri Sembilan": [
        "Negri Sembilan"
    ],
    "Sir Hugh Charles Clifford": [
        "H. C. Clifford",
        "Hugh Clifford",
        "Hugh Charles Clifford",
        "Clifford, H. C.",
        "Clifford"
    ],
    "Communism": [
        "Commmunist"
    ],
    "Edred John Henry Corner": [
        "E. J. H. Corner",
        "E.J.H. Corner",
        "Edred J. H. Corner",
        "Edred Corner",
        "Corner, E. J. H.",
        "Corner, E.J.H."
    ],
    "Crimes and criminals": [
        "Crimes",
        "Criminals"
    ],
    "Dayaks": [
        "Sea Dayaks",
        "Land Dayaks",
        "Iban",
        "Dayak",
        "Dyaks"
    ],
    "Decoration and ornament": [
        "Decorations",
        "Ornaments"
    ],
    "Nicholas Belfield Dennys": [
        "N. B. Dennys",
        "Dennys, N. B.",
        "N.B. Dennys"
    ]
    "Jacques de Coutre": [
        "de Coutre"
    ],
    "Tunku Dhiauddin ibn Sultan Zainal Rashid I": [
        "Dhiauddin ibn Sultan Zainal Rashid I",
        "Tunku Dhiauddin"
    ],
    "Dialects and dictionaries": [
        "Dialect",
        "Dictionary",
        "Dictionaries"
    ],
    "Jakarta": [
        "Djakarta", "Batavia"
    ],
    "Djalan Sampoerna": [
        "Djalan Sempoerna"
    ],
    "William Bloomfield Douglas": [
        "Bloomfield Douglas",
        "Captain William Bloomfield Douglas",
        "Captain Bloomfield Douglas",
        "W.B. Douglas",
        "W. B. Douglas"
    ],
    "Dragonflies": [
        "Dragon-flies"
    ],
    "Dutch East India Company": [
        "East India Company (Dutch)",
        "Vereenigde Oost-Indische Compagnie",
        "VOC",
        "V.O.C."
    ],
    "Dyes and dyeing": [
        "Dyes", "Dyeing"
    ],
    "George Windsor Earl": [
        "George Windsor Samuel Earl"
    ],
    "East India Company": [
        "EIC",
        "E.I.C."
    ],
    "Banks and banking": [
        "Banks",
        "Banking"
    ],
    "Manuel Godinho de Erédia": [
        "Manuel Godinho de Eredia",
        "M. G. de Eredia",
        "M.G. de Eredia"
    ],
    "Malay etiquette": [
        "Malay manners",
        "Court etiquette",
        "Court language"
    ],
    "Ivor Hugh Norman Evans": [
        "I. H. N. Evans",
        "I.H.N. Evans",
        "Ivan Evans",
    ],
    "Sir Robert Townsend Farquhar": [
        "Robert Faruhar",
        "Robert Townsend Farquhar",
        "Farquhar"
    ],
    "Federated Malay States": [
        "FMS",
        "F.M.S."
    ],
    "Forests and forestry": [
        "Forests",
        "Forestry"
    ],
    "France and the French": [
        "France", "French"
    ],
    "Funeral rites and ceremonies": [
        "Funerals", "Funeral rites", "Funeral ceremonies"
    ],
    "Carl Alexander Gibson-Hill": [
        "C. A. Gibson-Hill",
        "Gibson-Hill",
        "C.A. Gibson-Hill",
        "Carl A. Gibson-Hill"
    ],
    "John Desmond Gimlette": [
        "J. D. Gimlette"
    ],
    "John Michael Gullick": [
        "J. M. Gullick",
        "Gullick",
        "J.M. Gullick"
    ],
    "Gums and resins": [
        "Gums", "Resins"
    ],
    "Heritage and conservation": [
        "Heritage", "Conservation"
    ],
    "Dudley Francis Amelius Hervey": [
        "D.F.A. Hervey",
        "D. F. A. Hervey",
        "Dudley Hervey"
    ],
    "Anthony Haydock Hill": [
        "A. H. Hill",
        "A.H. Hill",
        "Anthony Hill"
    ],
    "Bishop George Frederick Hose": [
        "Bishop G. F. Hose",
        "G. F. Hose",
        "Bishop Hose",
        "George Hose",
        "G.F. Hose"
    ],
    "Houses and shophouses": [
        "Houses", "Shophouses"
    ],
    "Hunting and trapping": [
        "Hunting", "Trapping"
    ],
    "Ismail Abdul Rahman": [
        "Tun Dato' Dr. Haji Ismail bin Dato' Haji Abdul Rahman",
        "Tun Dr. Ismail Al-Haj bin Datuk Haji Abdul Rahman",
        "Dr. Ismail Abdul Rahman",
        "Tun Dato' Ismail Abdul Rahman",
        "Tun Dr. Ismail Abdul Rahman"
    ],
    "Kampong Banggul Ara": [
        "Kg Banggul Ara", "Banggul Ara"
    ],
    "Kampong Ipoh": [
        "Kg Ipoh"
    ],
    "Kedah": [
        "Queddah", "Quedda"
    ],
    "Henry Robert Kelham": [
        "H.R. Kelham", "H. R. Kelham", "Henry Kelham"
    ],
    "Keris": [
        "Kris"
    ],
    "Sir Frank Swettenham": [
        "Swettenham, F. A.", 
        "Frank Swettenham", 
        "Swettenham", 
        "F. A. Swettenham",
        "F.A. Swettenham",
        "Frank Athelstane Swettenham"
    ],
    "Sultan Ibrahim ibni Sultan Abu Bakar": [
        "Sultan Ibrahim of Johor",
        "Sultan Ibrahim ibn Sultan Abu Bakar",
        "Sir Ibrahim ibni Sultan Abu Bakar",
        "Ibrahim of Johor"
    ]
}

# 3. Facets/subsections for your synthesis agent
subtopics = {
    "Abdul Rahman ibni al-Marhum Tuanku Mohamed Shah": [
        "Coronation"
    ],
    "Munshi Abdullah": [
        "Life",
        "Works"
    ]
    "Archaeology": [
        "Borneo", "China, Indonesia, Thailand", "Malaya", "Periodic progress reports", "Sumatra"
    ],
    "Architecture": [
        "Singapore", "Southeast Asia", "Malaya"
    ],
    "Art": [
        "Pictorial", "Sculpture and artefacts"
    ]
    "Singapore": [
        "Architecture",
        "Commerce",
        "History", 
        "Economy",
        "Politics and government"
    ],
    "Malaya": [
        "Architecture",
        "Commerce",
        "Economy",
        "History",
        "Bibliography",
        "Politics and government",
        "Constitution",
        "Japanese invasion and occupation"
    ],
    "Penang": [
        "History",
        "Commerce"
    ],
    "Melaka": [
        "Commerce",
        "History",
        "Fortifications"
    ],
    "Perak": [
        "History"
    ],
    "Borneo": [
        "Antiquities",
        "Description and travel",
        "History",
        "Customary law"
    ],
    "Pahang": [
        "History"
    ],
    "Kedah": [
        "Antiquities"
    ],
    "Negeri Sembilan": [
        "Custom and constitution",
        "Genealogies"
    ],
    "Johor": [
        "Description and travel",
        "Economy",
        "History",
        "Antiquities",
        "Name"
    ],
    "Kedah": [
        "Antiquities", "Description and travel", "History"
    ]
    "Brunei": [
        "History",
        "Description and travel",
        "Kings and rulers"
    ],
    "Burma": [
        "History"
    ],
    "Thailand": [
        "History",
        "Description and travel"
    ],
    "China": [
        "Description and travel",
        "Commerce with SEA",
        "External relations with SEA",
        "Chinese in Malaysia",
        "Kings and rulers"
    ],
    "Indonesia": [
        "Antiquities", "Commerce", "Culture and society", "History"
    ]
    "Orang Asli": [
        "Dialects"
    ],
    "Botany": [
        "Christmas Island", "Malaya", "Singapore", "Southeast Asia (excluding Malaya and Singapore)"
    ],
    "Customary law": [
        "Borneo", "Malaya"
    ],
    "Ethnography": [
        "Borneo", "Fiji, Formosa, and Indo-China", "Malaya", "Orang Asli", "Singapore and Riau", "Sumatra", "Thailand"
    ]
    "Medicine": [
        "Traditional Medicine", "Western Medicine"
    ],
    "Boats": [
        "Sailing boats", "Fishing boats"
    ]
    "Marriage": [
        "Law and customs"
    ],
    "Flowers": [
        "In poetry"
    ],
    "Folklore": [
        "Borneo", "Malay", "China, Indo-China, and Indonesia", "Animals", "Malay Commentaries", "Princes, founders, and myths of origin", "Malay Villages", "Orang Asli"
    ],
    "Languages": [
        "Malay", "Tamil", "Chinese", "English"
    ]
    "Malay literature": [
        "Poetry", "Prose", "Proverbs and sayings"
    ],
    "Islam:": [
        "Coming to Southeast Asia", "Mysticism", "Law and theology"
    ],
    "Kelantan": [
        "Antiquities", "Description and travel", "History"
    ]
}

# 4. Thematic graph edges for downstream knowledge mapping
related = {
    "Agriculture": [
        "Land tenure", "Rice", "Tapioca", "Coconuts", "Durian", "Coffee", "Cocoa"
    ],
    "Raja Ali Haji": [
        "Bugis"
    ],
    "Alphabet": [
        "Languages: Malay"
    ],
    "Amok": [
        "Latah"
    ],
    "Amulets": [
        "Charms", "Medicine: Traditional", "Magic"
    ],
    "Anglo-Burmese War": [
        "Burma"
    ],
    "Animals": [
        "Folklore", "Hunting and trapping", "Mammals", "Natural history", "Superstitions", "Zoology"
    ],
    "Physical anthropology": [
        "Prehistoric Man"
    ],
    "Archery": [
        "Arms and armour"
    ],
    "Architecture": [
        "Churches", "Houses and shophouses", "Fortifications", "Temples"
    ],
    "Archives": [
        "Manuscripts"
    ],
    "Arms and armour": [
        "Keris", "Knives"
    ],
    "Art": [
        "Antiquities", "Archaeology", "Idols"
    ],
    "Babas": [
        "Peranakan", "Chinese", "Languages: Peninsular dialects"
    ],
    "Joseph Balestier": [
        "USA"
    ],
    "Joseph Alexander Bannerman": [
        "Penang: History"
    ],
    "Duarte Barbosa": [
        "Melaka: Commerce"
    ],
    "Basel Mission in North Borneo": [
        "Chinese in Malaysia", "Christianity"
    ],
    "Bataks": [
        "Ethnography: Sumatra"
    ],
    "Odoardo Beccari": [
        "Botanists and Botanical gardens"
    ],
    "Botany": [
        "Botanists and Botanical gardens", "Dyes and dyeing", "Ferns", "Fertilisation of plants", "Forest produce", "Fruit", "Grasses", "Herbs", "Malaya: Antiquities", "Medicine: Traditional", "Oilseed plants", "Plants", "Poisons and poisonous plants", "Rubber industry and plants", "Shrubs", "Trees"
    ],
    "Borneo": [
        "Beads", "Bajau", "Amulets", "Botany", "Dayaks", "Dusuns", 
        "Illanuns", "Kelabits", "Kenyah", "Maloh", "Melanus", 
        "Muruts", "Orang Belait", "Penan", "Rungus", "Sabah", "Sarawak", "Folklore: Borneo"
    ],
    "Brass-founding": [
        "Metal-work"
    ],
    "Britain in Malaya and Borneo": [
        "Colonial Civil Service", "Malaya: History"
    ],
    "Brunei": [
        "Archeology: Brunei", "Archives", "Cardinal points", "Charms", "China", "Coal mines", "Coins", "Customary law: Borneo", "Malay geneologies", "Inscriptions", "Languages: Malay", "English Literature", "Malaysia: History", "Malay Manuscripts", "Museums", "Sultan Omar Ali", "Orang Belait", "Radio-carbon dating", "Rites and ceremonies", "Sabah", "Sarawak", "Tombs and tombstones"
    ],
    "Bugis": [
        "Celebes"
    ],
    "Calculi": [
        "Medicine: Traditional"
    ],
    "Cambridge University Expedition": [
        "Walter William Skeat", "Thailand: Description and travel"
    ],
    "Ceramics": [
        "Pottery"
    ],
    "Charms": [
        "Incantations", "Magic"
    ],
    "Che Wong": [
        "Orang Asli"
    ],
    "Cheng Ho": [
        "China: Description and travel"
    ],
    "Chinese in Malaysia": [
        "Keramat", "Malaya: History", "Malaya: Politics and government", "Malaya: Japanese invasion and occupation", "Secret societies", "Street names"
    ],
    "Chinese in Singapore": [
        "Penang: History", "Street names"
    ],
    "Coal": [
        "Coal mines",
    ],
    "Communism": [
        "Malaya: Politics and government", "Singapore: Politics and government"
    ],
    "Contract labour": [
        "Labour in Java"
    ],
    "Gaspar Correa": [
        "Melaka: History"
    ],
    "Abraham Couperus": [
        "Melaka: History"
    ],
    "Currency": [
        "Coins", "Money", "Customary law: Borneo"
    ],
    "Customary law": [
        "Customary law: Borneo", "Customary law: Malaya", "Land tenure", "Negeri Sembilan: Custom and constitution", "Law: Malay texts", "Law: Western Law", "Law: Traditional Law", "Menangkabau"
    ],
    "Divorce": [
        "Marriage: Law and customs"
    ],
    "Bronze drums": [
        "Bronzes", "Kettledrums", "Prehistoric Man"
    ],
    "Dusuns": [
        "Ethnography: Borneo", "Mountains"
    ],
    "Dutch in Malaya": [
        "Dutch East India Company", "Melaka: History", "Languages: Dutch"
    ],
    "East India Company": [
        "Dutch East India Company", "Britain in Malaya and Borneo", "Britain in Southeast Asia"
    ],
    "Education": [
        "Islam", "Universities and colleges"
    ],
    "Manuel Godinho de Erédia": [
        "Melaka: Description and travel"
    ],
    "Ethnography": [
        "Archaeology", "Arms and armour", "Customary law", "Folklore", "Folktales", "Law", "Malay Custom", "Prehistoric Man", "Rites and ceremonies", "Superstitions"
    ],
    "Explorers": [
        "Travel and descriptions"
    ],
    "J. W. Farren": [
        "Philippines"
    ],
    "Fasts and feasts": [
        "Islam"
    ],
    "Pierre Étienne Lazare Favre": [
        "Languages: Malay", "Dialects and dictionaries"
    ],
    "Flint": [
        "Stone age"
    ],
    "Flowers": [
        "Literature: Poetry", "Malay Poetry", "Folklore: Borneo"
    ],
    "Folklore": [
        "Superstitions"
    ],
    "Funeral rites and ceremonies": [
        "Amulets", "Caves", "Rites and ceremonies", "Tombs and tombstones"
    ],
    "Hang Tuah": [
        "Malay literature", "Malaya: History", "Hang Jebat"
    ]
    "Hang Jebat": [
        "Hang Tuah", "Malay literature", "Malaya: History"
    ],
    "Houses and shophouses": [
        "Architecture", "Furniture", "Towns and town planning"
    ],
    "Inas": [
        "Negeri Sembilan: History"
    ],
    "Indo-China": [
        "Cambodia", "Ethnography: Fiji, Formosa, and Indo-China", "Folklore", "France and the French", "Islam: Coming to Southeast Asia", "Laos", "Vietnam"
    ],
    "Indonesia": [
        "Boats", "Bugis", "Celebes", "Southeast Asia: Commerce", "Borneo", "Islam: Coming to Southeast Asia", "Java", "Land tenure", "Stamford Raffles", "Sumatra"
    ],
    "Inscriptions": [
        "Seals", "Tombs and tombstones"
    ],
    "Sultan Iskander Shah": [
        "Melaka: History"
    ],
    "Islam": [
        "Calendar", "Fasts and feasts", "Malay culture and society", "Mosques and surau", "Saints", "Southeast Asia: Culture and society", "Inscriptions"
    ],
    "Japan": [
        "Malaya: Japanese invasion and occupation", "Southeast Asia: History"
    ],
    "Java": [
        "Dutch", "Indonesia", "Labour", "Land tenure", "Stamford Raffles"
    ],
    "Jawi alphabet": [
        "Languages: Malay"
    ],
    "Jelubu": [
        "Malay literature: Proverbs and sayings", "Negeri Sembilan: Custom and constitution"
    ],
    "Johor": [
        "Agriculture", "Coins", "Geology", "Inscriptions", "Kangchu System", "Land tenure", "Mines and mineral resources", "Orang Asli", "Regalia", "Johor Lama"
    ],
    "Kedah": [
        "Archaeology", "Architecture", "Botany: Malaya", "Bronzes": "Buddhism", "Cardinal points", "Coins", "Crimes and criminals", "Customary law: Malaya", "Dancing", "Inscriptions", "Law", "Languages: Malay", "Languages: Peninsular Dialects", "Francis Light", "Malay culture and society", "Mines and mineral resources", "Natural history", "Orang Asli"
    ],
    "Kelantan": [
        "Archaeology", "Birds", "Bulls and bull-fights", "Chinese in Malaysia", "Coins", "Robert William Duff", "Fisheries", "Games", "Geology", "Kites", "Languages: Malay", "Languages: Peninsular Dialects", "Malay culture and society", "Rice cultivation", "Shadow plays", "Silversmithing and silverware", "Theatre", "Weavers"
    ],
    "Keramat": [
        "Saints", "Tombs and tombstones"
    ]
}

# 5. Words that should be redirected

redirects = {
    "Aborigines": "Orang Asli",
    "Acridiidae": "Orthoptera",
    "Acting": "Theatre",
    "Actors": "Theatre",
    "Actresses": "Theatre",
    "Adat law": "Customary law",
    "Administrative law": "Law",
    "Aerial photography in archaeology": "Archaeology",
    "Social anthropology": "Ethnography",
    "Antiquities": "Archaeology",
    "Arabs": "South East Asia",
    "Arabia": "South East Asia",
    "Arachnids": "Spiders",
    "Armed forces": "Malayan Armed Forces",
    "Arhropods": "Insects",
    "Artillery": "Cannon",
    "Astronomy": "Calendar",
    "Malay authors": "Malay literature",
    "Bagan (Johor)": "Malay culture and society",
    "Balambangan Island": "Borneo",
    "Balambangan": "Borneo",
    "Balinese poetry": "Malay literature",
    "Banggai": "Bajau",
    "Baptist Mission Press": "Printing",
    "Bark cloth": "Stone age",
    "Barnacles": "Cirripedia",
    "Baths": "Medicine: Traditional",
    "Batu aceh": "Tombs and tombstones",
    "Batu Gajah": "Perak: History",
    "Batu Lawi": "Borneo: Description and travel",
    "Beliefs": "Superstitions",
    "Bendahara": "Pahang: History",
    "Benzoin": "Forest products",
    "Besisi dialects": "Orang Asli: Dialects",
    "Betrothal": "Marriage",
    "Courtship": "Marriage",
    "Bezoar": "Medicine: Traditional",
    "Guliga": "Medicine: Traditional",
    "Bibliography": "Malaya: Bibliography",
    "Bidayat al-Muhtadi bi-Fadl Allah al-Muhdi": "Malay Manuscripts",
    "Bidayuh": "Dayaks",
    "Blatteria": "Cockroaches",
    "Blattidae": "Cockroaches",
    "Blattoides": "Cockroaches",
    "Bleaching": "Dyes and dyeing",
    "Boar": "Pigs",
    "Body temperature": "Medicine: Western",
    "Bomoh": "Medicine: Traditional",
    "Boria": "Fasts and Feasts",
    "Boria": "Musical instruments and music",
    "British North Borneo": "Sabah",
    "Bruas": "Perak: History",
    "Bujang": "Mountains",
    "Carnivores": "Mammals",
    "Cemeteries": "Tombs and tombstones",
    "Census": "Population",
    "Cervidae": "Deer",
    "Champa": "Indo-China",
    "Chandi Bukit Batu Pahat": "Kedah: Antiquities",
    "Cheiroptera": "Bats",
    "Chelonia": "Turtles",
    "Cities": "Towns and town planning",
    "Clans": "Negeri Sembilan: Custom and constitution",
    "Climate": "Meteorology",
    "Clothing": "Dyes and dyeing",
    "Clothing": "Hats",
    "Clothing": "Weavers",
    "Coelenterata": "Sponges",
    "Coffins": "Tombs and tombstones",
    "Coleoptera": "Beetles",
    "Colleges": "Education",
    "Primitive commmunications": "Ethnography: Borneo",
    "Compass": "Cardinal points",
    "Convicts": "Prisons",
    "Cremation": "Funeral rites and ceremonies",
    "Dayak language": "Language: Borneo and Sumatra",
    "Death register": "Register of births"
    "Decapoda": "Lobsters",
    "Crustacea": "Lobsters",
    "Demography": "Population",
    "Decorative design": "Art: Sculpture and artefacts",
    "Chinese language": "Languages: Chinese",
    "Diet": "Medicine: Western",
    "Western Dipanagara": "Java",
    "Diptera": "Flies",
    "Disease": "Medicine",
    "Diseases": "Medicine",
    "Documents": "Archives",
    "Dogfish": "Fish",
    "Dormice": "Rodentia",
    "Earthworks": "Fortifications",
    "Emancipation": "Slavery and debt bondage",
    "Emperors": "China: Kings and rulers",
    "Entomology": "Insects",
    "Entomostraca": "Cirripedia",
    "Epigrams": "Malay literature",
    "Epitaphs": "Inscriptions",
    "Epitaphs": "Tombs and tombstones"
    "Estates": "Rubber industry",
    "Etymology": "Languages",
    "Excretion": "Medicine: Western",
    "Extraterritoriality": "Thailand: History",
    "Fa-Hsien": "Buddha",
    "Fa-Hsien": "Buddhism",
    "Fables": "Folktales",
    "Fauna": "Zoology",
    "Federated Malay States": "Malaya: Constitution",
    "Festivals": "Fasts and feasts",
    "Forced labour": "Labour",
    "Formicidae": "Ants",
    "Formosa": "Ethnography: Fiji, Formosa, and Indo-China",
    "Fortifications": "Melaka: Fortifications",
    "Gemenceh": "Negeri Sembilan: Genealogies",
    "Gordonia": "Trees",
    "Gordonia": "Grasses",
    "Graves": "Funeral rites and ceremonies",
    "Graves": "Tombs and tombstones",
    "Gunong": "Mountains",
    "Gunung": "Mountains",
    "Harvest festivals": "Rites and ceremonies",
    "Herpetology": "Reptiles",
    "Heterocera": "Moths",
    "Hikayat": "Malay literature: Prose",
    "Hikayat Abdullah": "Munshi Abdullah bin Abdul Kadir",
    "Hydrophiidae": "Sea-snakes",
    "Hypericales": "Dipterocarpaceae"
    "Ibans": "Dayaks",
    "Modern industries": "Technology",
    "Primative industries": "Archaeology",
    "Insectivora": "Tupaia",
    "Irrigation": "Rice cultivation",
    "Jewellery": "Gold mines",
    "Jinn": "Superstitions",
    "Justice": "Law",
    "Journalism": "Newspapers",
    "Kalabits": "Kelabits",
    "Kerdau": "Pahang"
}

# 6. Topic/Thematic clusters (Aggregators for synthesis, NOT direct extraction entities)
clusters = {
    "Archaeological finds": [
        "Amulets",
        "Arms and armour",
        "Bronzes",
        "Caves",
        "Coins",
        "Ethnography",
        "Funeral rites and ceremonies",
        "Inscriptions",
        "Iron age",
        "Man, prehistoric",
        "Pottery",
        "Stone age",
        "Temples",
        "Tombs and tombstones"
    ],
    "Animals": [
        "Ants",
        "Apes",
        "Badgers",
        "Bats",
        "Bees",
        "Beetles",
        "Birds",
        "Buffaloes",
        "Bullocks",
        "Butterflies",
        "Cattle",
        "Centipedes",
        "Crabs",
        "Crocodiles",
        "Deer",
        "Dogs",
        "Dragonflies",
        "Elephants",
        "Flies",
        "Frogs",
        "Gibbons",
        "Goats",
        "Lobsters",
        "Tigers",
        "Turtles",
        "Moths",
        "Butterflies",
        "Fireflies",
        "Sea-snakes",
        "Wasps"
    ],
    "Crimes and criminals": [
        "Crimes", "Criminals", "Convicts", "Prisons"
    ]
    "Amusements": [
        "Bulls and bull-fights",
        "Cards",
        "Dancing",
        "Games",
        "Kites",
        "Shadow plays",
        "Theatre"
    ],
    "Aculeata": [
        "Ants", "Bees", "Wasps"
    ],
    "Birds": [
        "Cockatoos",
        "Cuckoos",
        "Falcons",
        "Flight",
        "Gulls",
        "Hawks",
        "Horn-bills",
        "Owls"
    ],
    "Botany": [
        "Flowers", "Fertilisation"
    ]
    "Demonology": [
        "Amulets", "Charms", "Exorcism", "Magic", "Superstitions", "Witchcraft", "Hallucinations", "Illusions", "Hysteria"
    ],
    "Family": [
        "Malay culture and society", "Divorce", "Marriage", "Menangkabau", "Negeri Sembilan: Custom and constitution"
    ]
    "Fruit": [
        "Bananas",
        "Durian",
        "Pineapple",
        "Cocoa",
        "Coconuts"
    ],
    "Economics": [
        "Banks and banking",
        "Labour in Malaya",
        "Population",
        "Finance",
        "Ban Hin Lee Bank",
        "Currency",
        "Money",
        "Exchange",
        "Coins"
    ],
    "Commerce": [
        "Harbours", "Money", "Smuggling", "Melaka: Commerce"
    ],
    "Dialects and dictionaries": [
        "Languages: Chinese",
        "Languages: Malay",
        "Languages: Tamil",
        "Languages: English",
        "Languages: Dutch",
        "Languages: Portuguese",
        "Languages: Sanskrit",
        "Languages: Peninsular dialects"
    ],
    "Disasters": [
        "Earthquakes", "Floods", "Lightning", "Meteorites"
    ],
    "Emblems": [
        "Flags", "Regalia", "Seals"
    ],
    "European": [
        "Britain",
        "Christianity",
        "Dutch",
        "Education",
        "France and the French",
        "Germany",
        "Medicine: Western",
        "Portugal and the Portuguese",
        "Southeast Asia: History",
        "Technology",
        "USA"
    ],
    "Foreign relations": [
        "Britain in Borneo",
        "Britain in Malaya",
        "Britain",
        "Dutch",
        "France and the French",
        "Germany",
        "Portugal and the Portuguese",
        "Southeast Asia",
        "USA",
        "China",
        "Indonesia",
        "Thailand",
        "Southeast Asia: Civilisation",
        "Japan",
        "India"
    ],
    "Foreign trade": [
        "Britain in Borneo",
        "Britain in Malaya",
        "Britain",
        "Dutch",
        "France and the French",
        "Germany",
        "Portugal and the Portuguese",
        "Southeast Asia",
        "USA",
        "China",
        "Indonesia",
        "Thailand",
        "Southeast Asia: Commerce",
        "Japan",
        "India"
    ],
    "Games": [
        "Cards",
        "Kites",
        "Hua-hoey",
        "Lottery",
        "Chap-ji-ki",
        "Chess",
        "Chinese games",
        "Chongkak",
        "Malay games"
    ],
    "History": [
        "Archaeology", "Ethnography", "Genealogy", "Seals", "Kings and rulers", "Politics and government"
    ],
    "Hymenoptera": [
        "Bees", "Wasps", "Ants"
    ],
    "Implements": [
        "Tools",
        "Utensils",
        "Bronzes"
    ],
    "Insects": [
        "Ants", "Bees", "Beetles", "Butterflies", "Fertilisation", "Hymenoptera", "Larvae", "Moths", "Orthoptera", "Wasps", "Fireflies"
    ],
    "Invertebtrates": [
        "Insects", "Molluscs", "Sponges"
    ],    
    "Religion": [
        "Buddha",
        "Buddhism",
        "Islam",
        "Muslim",
        "Christianity",
        "Jesus",
        "Hinduism",
        "Hindu",
        "Judaism",
        "Jews",
        "Catholic",
        "Anglican",
        "Animism",
        "Paganism"
    ],
    "Music": [
        "Musical instruments",
        "Gamelan"
    ]
    "Architecture": [
        "Buildings", "Houses and shophouses", "Mosques and surau", "Temples"
    ]
}