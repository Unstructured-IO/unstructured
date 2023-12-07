import itertools
import json
import multiprocessing as mp
import typing as t
import uuid
from dataclasses import dataclass

from unstructured.ingest.error import DestinationConnectionError, WriteError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDoc,
    ConfigSessionHandleMixin,
    IngestDocSessionHandleMixin,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies
from unstructured.staging.base import flatten_dict

# if t.TYPE_CHECKING:
#     from pinecone import Index as PineconeIndex


@dataclass
class SimpleChromaConfig(ConfigSessionHandleMixin, BaseConnectorConfig):
    # index_name: str
    # environment: str
    # api_key: str = enhanced_field(sensitive=True)
    db_path: str
    collection_name: str


@dataclass
class ChromaWriteConfig(WriteConfig):
    # breakpoint()
    # batch_size: int = 50
    num_processes: int = 1

# @dataclass
# class ChromaSessionHandle(BaseSessionHandle):
#     service: "ChromaIndex"

# @DestinationConnectionError.wrap
# @requires_dependencies(["chromadb"], extras="chroma")
# def create_chroma_object(self, db_path, collection_name): #api_key, index_name, environment): # maybe chroma client?
#     import chromadb

#     chroma_client = chromadb.PersistentClient(path=db_path)
#     print("** getting client **")
#     print(chroma_client)
#     collection = chroma_client.get_or_create_collection(name=collection_name)

#     # chroma.init(api_key=api_key, environment=environment)
#     # index = pinecone.Index(index_name)
#     # logger.debug(f"Connected to index: {pinecone.describe_index(index_name)}")
#     return collection

# @dataclass
# class ChromaWriteConfig(ConfigSessionHandleMixin, WriteConfig):
#     db_path: str # RENAME CLIENT
#     collection_name: str
    # api_key: str
    # index_name: str
    # environment: str
    # todo: fix buggy session handle implementation
    # with the bug, session handle gets created for each batch,
    # rather than with each process


    # def create_session_handle(self) -> ChromaSessionHandle:
    #     service = self.create_chroma_object(self.db_path, self.collection_name)
    #     return ChromaSessionHandle(service=service)

    # @requires_dependencies(["chromadb"], extras="chroma")
    # def upsert_batch(self, batch):

    #     collection = self.session_handle.service
    #     print(collection)

    #     try:
    #         # Chroma wants lists even if there is only one element
    #         response = collection.add(ids=[batch["ids"]], documents=[batch["documents"]], embeddings=[batch["embeddings"]], metadatas=[batch["metadatas"]])
    #     except Exception as e:
    #         raise WriteError(f"chroma error: {e}") from e
    #     logger.debug(f"results: {response}")

aaa=({'ids': ['94d7dea0-3ea6-4aa4-8a56-053a4105e08e', 'ea0fb9d5-b363-4076-b17d-6e6ce6bf74ec'], 
'documents': ['CHAPTER I\n\n"Well, Prince, so Genoa and Lucca are now just family estates of the Buonapartes. But I warn you, if you don\'t tell me that this means war, if you still try to defend the infamies and horrors perpetrated by that Antichrist--I really believe he is Antichrist--I will have nothing more to do with you and you are no longer my friend, no longer my \'faithful slave,\' as you call yourself! But how do you do? I see I have frightened you--sit down and tell me all the news."\n\nIt was in July, 1805, and the speaker was the well-known Anna Pavlovna Scherer, maid of honor and favorite of the Empress Marya Fedorovna. With these words she greeted Prince Vasili Kuragin, a man of high rank and importance, who was the first to arrive at her reception. Anna Pavlovna had had a cough for some days. She was, as she said, suffering from la grippe; grippe being then a new word in St. Petersburg, used only by the elite.\n\nAll her invitations without exception, written in French, and delivered by a scarlet-liveried footman that morning, ran as follows:\n\n"If you have nothing better to do, Count (or Prince), and if the prospect of spending an evening with a poor invalid is not too terrible, I shall be very charmed to see you tonight between 7 and 10--Annette Scherer."', '"Heavens! what a virulent attack!" replied the prince, not in the least disconcerted by this reception. He had just entered, wearing an embroidered court uniform, knee breeches, and shoes, and had stars on his breast and a serene expression on his flat face. He spoke in that refined French in which our grandfathers not only spoke but thought, and with the gentle, patronizing intonation natural to a man of importance who had grown old in society and at court. He went up to Anna Pavlovna, kissed her hand, presenting to her his bald, scented, and shining head, and complacently seated himself on the sofa.\n\n"First of all, dear friend, tell me how you are. Set your friend\'s mind at rest," said he without altering his tone, beneath the politeness and affected sympathy of which indifference and even irony could be discerned.\n\n"Can one be well while suffering morally? Can one be calm in times like these if one has any feeling?" said Anna Pavlovna. "You are staying the whole evening, I hope?"\n\n"And the fete at the English ambassador\'s? Today is Wednesday. I must put in an appearance there," said the prince. "My daughter is coming for me to take me there."\n\n"I thought today\'s fete had been canceled. I confess all these festivities and fireworks are becoming wearisome."\n\n"If they had known that you wished it, the entertainment would have been put off," said the prince, who, like a wound-up clock, by force of habit said things he did not even wish to be believed.'], 
'embeddings': [
    [-0.10798826068639755, 0.07079049944877625, 0.03793809190392494, 0.06238418072462082, -0.0800926685333252, 0.08458053320646286, 0.04109042137861252, 0.01411767303943634, -0.026673296466469765, -0.06834850460290909, -0.05604946240782738, -0.002084247302263975, 0.05413816496729851, -0.11277893930673599, -0.13420690596103668, 0.01921900361776352, -0.0016900176415219903, 0.05590571090579033, 0.01585039310157299, 0.1647440791130066, -0.004285052418708801, -0.04817255586385727, 0.0315268337726593, 0.0935421884059906, 0.027134746313095093, 0.032464031130075455, -0.01579393818974495, -0.013843133114278316, -0.02163640968501568, 0.060567211359739304, -0.049173641949892044, -0.016232207417488098, 0.032136350870132446, -0.010719413869082928, 0.007659754250198603, -0.02357594110071659, 0.05389918386936188, 0.01903712749481201, 0.03225841373205185, 0.0030333937611430883, 0.01985984668135643, -0.012277006171643734, 0.0036048172041773796, 0.07216695696115494, -0.03389861434698105, -0.04034867882728577, -0.09797950088977814, 0.09287519007921219, -0.04085979610681534, -0.07710124552249908, -0.06075974181294441, 0.014204251579940319, -0.03130774945020676, -0.03590141981840134, -0.029338574036955833, 0.0494147464632988, -0.02514871023595333, -0.032197851687669754, 0.00956161879003048, 0.03868991136550903, -0.01540116686373949, 0.05488169938325882, 0.08505600690841675, 0.05001736059784889, -0.04215556010603905, -0.06236148625612259, 0.041096094995737076, 0.04524005204439163, -0.0050820717588067055, 0.09457061439752579, -0.007427291013300419, 0.02646271511912346, 0.0240954402834177, -0.038618020713329315, -0.04922528192400932, -0.029858453199267387, 0.06573119759559631, -0.028649788349866867, -0.040935780853033066, -0.03981170803308487, -0.029753953218460083, -0.032603669911623, 0.010047676041722298, 0.03241921216249466, -0.0727785974740982, -0.0879196971654892, 0.04625425115227699, -0.057965606451034546, 0.06541603058576584, 0.002971641719341278, 0.04304951801896095, -0.029508598148822784, -0.046845968812704086, 0.019637243822216988, 0.038244638592004776, -0.022009989246726036, -0.08398984372615814, 0.10692594200372696, -0.008123187348246574, 0.04122510924935341, 0.009356506168842316, 0.02497430518269539, 0.030136989429593086, 0.03120807558298111, -0.06865032762289047, -0.01691349223256111, -0.02474832348525524, -0.1197269856929779, -0.05192697420716286, -0.029380299150943756, -0.05458355322480202, -0.07207832485437393, 0.024856584146618843, -0.10557802021503448, -0.03888874500989914, 0.14399847388267517, 0.01865619234740734, -0.015178651548922062, 0.01510833390057087, -0.005753480363637209, 0.03219407796859741, -0.010148520581424236, -0.03800737485289574, 0.10337431728839874, 0.011906363070011139, 0.0026586914900690317, 0.029026545584201813, -3.3116527354819545e-34, 0.01634507067501545, -0.027912698686122894, 0.06738336384296417, 0.06168054789304733, -0.0018871105276048183, -0.00132972642313689, -0.011837519705295563, -0.030090896412730217, -0.05317867547273636, -0.01967674493789673, 0.017086388543248177, -0.016405845060944557, -0.02356661483645439, -0.05440527945756912, 0.004482890944927931, 0.06315705180168152, -0.062390200793743134, 0.015662511810660362, 0.02351364679634571, 0.022607209160923958, 0.11598236858844757, 0.019297726452350616, -0.04229110851883888, 0.04369564354419708, -0.0008442605030722916, 0.08734124898910522, 0.04909766465425491, 0.011995581910014153, 0.023195365443825722, 0.023311443626880646, 0.009395217522978783, -0.0005967718898318708, 0.030232030898332596, -0.032988958060741425, -0.011013614013791084, -0.009962338022887707, -0.04666011780500412, -0.10052923858165741, 0.0009428844787180424, -0.028231393545866013, -0.001659254776313901, -0.031029140576720238, -0.0005216523422859609, 0.015900392085313797, -0.06744205206632614, -0.06276901066303253, -0.030373677611351013, -0.04375403746962547, 0.04321721941232681, -0.04426367208361626, -0.020966188982129097, -0.06185345724225044, -0.011066759936511517, 0.14485512673854828, -0.011226754635572433, 0.039222605526447296, 0.008758807554841042, 0.06689213961362839, 0.062164194881916046, -0.06488236784934998, 0.025756215676665306, 0.005924362223595381, 0.028303220868110657, 0.030312249436974525, 0.020441841334104538, -0.054834749549627304, -0.035536594688892365, 0.08572821319103241, -0.020714273676276207, -0.016513412818312645, -0.04590507224202156, 0.03946381062269211, -0.03451549634337425, -0.009611116722226143, 0.04620583355426788, 0.020474063232541084, -0.012756388634443283, 0.010679338127374649, -0.037906475365161896, -0.030561624094843864, -0.02563626877963543, -0.011292705312371254, 0.012476067058742046, 0.06892282515764236, -0.053628917783498764, -0.06907674670219421, 0.0698268786072731, 0.022053569555282593, 0.008496589958667755, 0.06891883164644241, -0.013330754823982716, 0.03887031972408295, 0.06317520141601562, -0.028382189571857452, -0.16124063730239868, -2.0564166131552255e-33, -0.010592065751552582, -0.02760656177997589, -0.017936306074261665, 0.08073572814464569, -0.06017963960766792, -0.024169882759451866, -0.04754273220896721, 0.049563758075237274, 0.0003540913457982242, -0.08038360625505447, -0.029684273526072502, -0.04580100625753403, 0.0682189092040062, 0.016084162518382072, 0.017505716532468796, 0.03771026059985161, 0.06793203204870224, 0.1021241769194603, -0.08725901693105698, -0.008899052627384663, -0.03750333935022354, 0.048866622149944305, -0.10057011991739273, -0.015166027471423149, 0.037038013339042664, -0.0013394184643402696, 0.1664167195558548, -0.0067575047723948956, -0.11243391036987305, -0.007858487777411938, 0.005998619366437197, 0.006984880659729242, -0.11799252778291702, 0.06211281940340996, 0.012133435346186161, 0.020269611850380898, 0.0542217455804348, 0.028609847649931908, 0.046817902475595474, -0.019438739866018295, -0.04504735767841339, -0.00667444197461009, -0.0036811812315136194, 0.028774775564670563, 0.023280013352632523, 0.035102661699056625, 0.047387685626745224, 0.022496359422802925, 0.07940759509801865, 0.0424313023686409, -0.054501768201589584, -0.013033444061875343, -0.010813072323799133, 0.037235189229249954, -0.009556170552968979, -0.08640535920858383, -0.03191079944372177, -0.12135865539312363, 0.0239898432046175, 0.02504461444914341, 0.02176966890692711, 0.03268412500619888, -0.11259281635284424, -0.06788100302219391, 0.012991189025342464, -0.0218863133341074, -0.05397878214716911, 0.05800669640302658, 0.042348481714725494, -0.03504446893930435, -0.02746560052037239, -0.011551150120794773, -0.04563038423657417, 0.11079887300729752, 0.03751087561249733, 0.03910473361611366, -0.02992991916835308, -0.0848516970872879, -0.02262766845524311, -0.03159540519118309, -0.006123168859630823, -0.05333922803401947, 0.023491820320487022, -0.021088162437081337, 0.04904910922050476, 0.024003110826015472, 0.047515373677015305, 0.0005271305562928319, -0.02729189582169056, 0.004024899564683437, -0.04842270165681839, -0.0038308969233185053, 0.04580814018845558, -0.06006494536995888, -0.016371434554457664, -6.667781349278812e-08, 0.08489655703306198, 0.009835030883550644, 0.008675304241478443, -0.04072139412164688, 0.044173430651426315, -0.09124138951301575, -0.031109780073165894, -0.05103599280118942, -0.015294152311980724, 0.04114753007888794, -0.02546808309853077, -0.044520117342472076, 0.0708218663930893, -0.10130880028009415, 0.05403494834899902, -0.0031449254602193832, 0.028019368648529053, -0.055657949298620224, -0.07346204668283463, -0.07357041537761688, 0.05441804602742195, -0.015085402876138687, -0.022374477237462997, -0.11304542422294617, -0.010476930998265743, 0.04240499809384346, -0.005072653293609619, -0.030520271509885788, -0.0112220523878932, -0.023295938968658447, 0.0006029148935340345, 0.010359890758991241, -0.06605648249387741, 0.003729678923264146, -0.032053206115961075, 0.11255879700183868, 0.0435265451669693, -0.05158473551273346, 0.09309980273246765, -0.030521871522068977, 0.05256204307079315, 0.00022279738914221525, 0.006431682966649532, 0.017685381695628166, 0.051856230944395065, 0.018831130117177963, 0.002300737891346216, -0.1150611937046051, 0.048399802297353745, 0.06604171544313431, -0.0484318807721138, 0.06328118592500687, 0.020386971533298492, 0.10859765112400055, 0.0060322522185742855, 0.0019275337690487504, 0.02445015124976635, 0.06521134823560715, 0.003129055257886648, 0.02143748477101326, 0.014636674895882607, -0.029396915808320045, -0.06610259413719177, 0.012949924916028976], [-0.03397400677204132, 0.12694139778614044, 0.07854234427213669, 0.0018304819241166115, -0.01804310642182827, 0.05006016790866852, 0.09893957525491714, -0.027144402265548706, -0.06067163869738579, -0.058634042739868164, -0.057603973895311356, -0.016389356926083565, -0.020649239420890808, -0.0007989357109181583, 0.016281720250844955, 0.01987302117049694, -0.006202413234859705, 0.003468653652817011, -0.08389347791671753, 0.1988363265991211, -0.02766471356153488, 0.0043783183209598064, 0.03538069128990173, -0.010820243507623672, -0.09978920221328735, -6.213066808413714e-05, 0.044856131076812744, -0.050117071717977524, -0.027546564117074013, 0.0042617106810212135, -0.044911257922649384, -0.021353228017687798, -0.018461143597960472, 0.07077419012784958, -0.05679399520158768, 0.0491456463932991, -0.006780524272471666, -0.03416313976049423, 0.03257417678833008, -0.0013525041285902262, -0.007928239181637764, -0.059812031686306, -0.04234170541167259, 0.03939149156212807, 0.058330707252025604, 0.01372634805738926, -0.013883269391953945, 0.002186131663620472, -0.020768124610185623, -0.07475223392248154, -0.12359054386615753, 0.03477929159998894, -0.017173396423459053, -0.0298065934330225, -0.05695575848221779, 0.04160284250974655, 0.05150435119867325, 0.016356075182557106, 0.011040130630135536, 0.041076064109802246, -0.02449897862970829, 0.044571470469236374, 0.07027178257703781, 0.04427974298596382, -0.06284460425376892, -0.05624692142009735, 0.0731152668595314, 0.019471313804388046, -0.06037868186831474, 0.08853352069854736, 
    -0.0034970880951732397, -0.025149092078208923, 0.03059786558151245, -0.03739277273416519, -0.08096496015787125, -0.0031991498544812202, 0.04536398872733116, -0.08435793966054916, 0.008131306618452072, -0.006521447561681271, 0.005110510624945164, -0.02489815652370453, -0.06321306526660919, 0.007662492338567972, -0.05108276382088661, -0.1482323408126831, 0.05053076520562172, -0.055289238691329956, 0.031866054981946945, 0.029050232842564583, 0.004686734173446894, 0.021791735664010048, -0.02179674617946148, 0.032372213900089264, 0.10196683555841446, 0.0528903603553772, -0.013191170990467072, 0.0456242635846138, -0.11250840872526169, 0.08285089582204819, 0.05312855541706085, 0.0981115773320198, 0.006894479040056467, 0.03776193782687187, -0.050521403551101685, 0.010938447900116444, -0.06661766022443771, -0.09156814962625504, -0.07711920887231827, -0.016305221244692802, -0.06698641926050186, -0.037995461374521255, 0.017763691022992134, -0.12272297590970993, 0.004113514441996813, 0.05381679907441139, 0.009406057186424732, -0.043825048953294754, 0.010453351773321629, -0.015948163345456123, 0.0557393804192543, 0.030865924432873726, -0.020815419033169746, 0.1101209744811058, -0.02065049298107624, 0.0009824552107602358, 0.02336334064602852, 6.515963551279641e-33, 0.048798829317092896, 0.044213224202394485, 0.028411077335476875, 0.019670648500323296, -0.02156190760433674, 0.03759535402059555, -0.03159323334693909, -0.029584171250462532, -0.035116299986839294, -0.05703293904662132, 0.022406255826354027, -0.08849241584539413, 0.014585497789084911, -0.03905870020389557, -0.135045126080513, 0.07589839398860931, -0.029958153143525124, -0.043158262968063354, 0.023696379736065865, 0.02127073146402836, 0.015001577325165272, 0.05705941841006279, -0.010941940359771252, 0.03379526734352112, -0.11139602959156036, -0.016050195321440697, 0.0900421291589737, -0.0195343978703022, -0.009949379600584507, 0.02555369958281517, -0.03964032605290413, 0.00017527761519886553, 0.036811619997024536, -0.017886551097035408, 0.01994895376265049, -0.008487754501402378, -0.047552987933158875, -0.01929125003516674, -0.0548204705119133, -0.002770292339846492, -0.0040601338259875774, 0.035296179354190826, 0.020970817655324936, 0.02304244041442871, -0.09790085256099701, 0.04692431539297104, -0.049121759831905365, -0.007282267790287733, -0.04136241599917412, -0.02747730165719986, -0.008483920246362686, 0.0062732151709496975, 0.053738199174404144, -0.028291553258895874, -0.06067783758044243, -0.0012102731270715594, 0.045503128319978714, 0.05545952171087265, 0.03047923929989338, -0.09203436970710754, 0.06398262083530426, -0.031124137341976166, 0.04074641689658165, -0.030154576525092125, -0.04261225461959839, -0.08926401287317276, -0.09338711202144623, 0.0019085283856838942, -0.048413947224617004, -0.06485138088464737, -0.03952133655548096, 0.14852406084537506, 0.018340960144996643, -0.029525725170969963, -0.031372182071208954, 0.01130011584609747, -0.016319449990987778, -0.008824216201901436, 0.021405216306447983, -0.05395134165883064, 0.0002568592899478972, 0.02331569790840149, -0.05333240330219269, 0.048288825899362564, 0.03454647213220596, -0.10220237821340561, 0.007759599946439266, -0.05924929678440094, 0.007452998775988817, 0.14334793388843536, -0.021201884374022484, 0.025409389287233353, 0.058578308671712875, -0.09460382908582687, -0.08091404289007187, -8.492186286782839e-33, 0.027771199122071266, -0.014627973549067974, -0.09311514347791672, 0.15120406448841095, -0.01649477146565914, 0.003927209880203009, -0.07498050481081009, 0.04737090691924095, -0.012823843397200108, 0.0041934833861887455, -0.0017412428278476, -0.05210086330771446, 0.10518244653940201, -0.07292034476995468, -0.004470311105251312, -0.03480333834886551, 0.06769026070833206, 0.07186891883611679, -0.014370026998221874, 0.10009201616048813, 0.05009102821350098, 0.010746284388005733, -0.010329089127480984, -0.008813135325908661, -0.02039971947669983, 0.06421047449111938, 0.10569915175437927, -0.03189529478549957, -0.1177692860364914, -0.037893135100603104, 0.08056116104125977, 0.018323253840208054, -0.10049200803041458, 0.009066888131201267, 0.0004500770883169025, 0.07442380487918854, 0.03158092126250267, -0.04310248792171478, -0.006777468603104353, 0.0024325812701135874, -0.021089570596814156, -0.03740869462490082, -0.005152920261025429, 0.06441134959459305, 0.014739050529897213, -0.049763958901166916, -0.0070731486193835735, -0.0364321805536747, 0.021678293123841286, -0.0010973400203511119, -0.022440863773226738, 0.010661991313099861, -0.04659054055809975, 0.04007334262132645, 0.04300292208790779, -0.0693795382976532, -0.05999727174639702, -0.06438520550727844, 0.03210693597793579, 0.015350952744483948, -0.004875735379755497, -0.005926721263676882, -0.062389325350522995, -0.055526334792375565, -0.015559935010969639, 0.06300835311412811, -0.04413113370537758, 0.025567322969436646, 0.05198674276471138, 0.023768488317728043, 0.01800445467233658, 0.0059555452316999435, -0.03359314426779747, -0.02549477107822895, 0.05638403072953224, 0.05290402099490166, 0.06645572185516357, -0.05549173802137375, -0.010425609536468983, -0.036284059286117554, -0.01665792614221573, -0.08813489973545074, 0.0290748942643404, -0.06419026851654053, -0.038480013608932495, -0.037945039570331573, -0.007302526384592056, 0.049078959971666336, -0.054420772939920425, 0.027682675048708916, -0.012715869583189487, 0.03326112776994705, -0.011878148652613163, -0.04716692864894867, 0.07432813942432404, -7.89662237821176e-08, -0.004841025453060865, -0.08356941491365433, -0.0632082149386406, -0.03243472799658775, 0.007670063525438309, -0.05662892386317253, 0.0006755957729183137, -0.0416731983423233, -0.012796352617442608, 0.08044342696666718, 0.048724401742219925, -0.010512868873775005, -0.0004136273928452283, -0.014944315887987614, 0.049297381192445755, 0.020989250391721725, -0.004167370498180389, 0.008990109898149967, -0.08193770051002502, 0.05404585227370262, 0.03457047790288925, 0.024897651746869087, -0.024454152211546898, -0.02558487467467785, 0.00560530973598361, 0.0025735520757734776, -0.0016010206891223788, -0.056344904005527496, -0.07035011053085327, -0.006419958081096411, 0.05529171600937843, 0.056911636143922806, -0.07535190880298615, -0.0882006511092186, -0.04194745421409607, -0.03606702387332916, 0.05822581425309181, -0.046960871666669846, 0.12611953914165497, -0.001748613198287785, 0.02163792960345745, -0.024738404899835587, -0.051761023700237274, 0.026361770927906036, 0.09046662598848343, -0.03430228307843208, 0.008219504728913307, 0.01956736482679844, -0.0033476697281003, 0.032101698219776154, -0.0046179573982954025, -0.002105622086673975, 0.024813296273350716, 0.056636519730091095, 0.005778959486633539, 0.009783387184143066, 0.018273551017045975, 0.0649428740143776, -0.017756180837750435, 0.029473502188920975, 0.06680544465780258, 0.023304712027311325, -0.05768158659338951, -0.0574689581990242]], 
    'metadatas': [{'type': 'UncategorizedText', 'element_id': '01715d453d60a7fd335356188a122675', 'metadata-data_source-url': 'example-docs/book-war-and-peace-1p.txt', 'metadata-data_source-date_created': '2023-10-25 10:05:44.916316', 'metadata-data_source-date_modified': '2023-10-25 10:05:44.916316', 'metadata-data_source-date_processed': '2023-12-07T20:27:29.112501', 'metadata-data_source-permissions_data-0-mode': 33188, 'metadata-file_directory': 'example-docs', 'metadata-filename': 'book-war-and-peace-1p.txt', 'metadata-filetype': 'text/plain', 'metadata-languages-0': 'eng', 'metadata-last_modified': '2023-10-25T10:05:44'}, {'type': 'UncategorizedText', 'element_id': 'a88204a71ce491cd4feb9dc3cebc56ea', 'metadata-data_source-url': 'example-docs/book-war-and-peace-1p.txt', 'metadata-data_source-date_created': '2023-10-25 10:05:44.916316', 'metadata-data_source-date_modified': '2023-10-25 10:05:44.916316', 'metadata-data_source-date_processed': '2023-12-07T20:27:29.112501', 'metadata-data_source-permissions_data-0-mode': 33188, 'metadata-file_directory': 'example-docs', 'metadata-filename': 'book-war-and-peace-1p.txt', 'metadata-filetype': 'text/plain', 'metadata-languages-0': 'eng', 'metadata-last_modified': '2023-10-25T10:05:44'}]}
)


@dataclass
class SimpleChromaConfig(BaseConnectorConfig):
    # api_key: str
    # index_name: str
    # environment: str
    db_path: str
    collection_name: str


@dataclass
class ChromaDestinationConnector(BaseDestinationConnector): # IngestDocSessionHandleMixin,
    write_config: ChromaWriteConfig
    connector_config: SimpleChromaConfig
    _collection = None# : t.Optional["PineconeIndex"] = None

    @property
    def chroma_collection(self):
        if self._collection is None:
            self._collection = self.create_collection()
        return self._collection

    def initialize(self):
        pass

    @DestinationConnectionError.wrap
    def check_connection(self):
        create_chroma_object(
            self.db_path, self.collection_name
        )

    @requires_dependencies(["chromadb"], extras="chroma")
    def create_collection(self): #### -> "PineconeIndex":
        import chromadb
        chroma_client = chromadb.PersistentClient(path=self.connector_config.db_path)
        print("** getting client **")
        print(chroma_client)
        # breakpoint()
        collection = chroma_client.get_or_create_collection(name=self.connector_config.collection_name)
        print(collection)
        return collection

    # def create_index(self): #### -> "PineconeIndex":
    #     import chromadb

    #     pinecone.init(
    #         api_key=self.connector_config.api_key, environment=self.connector_config.environment
    #     )
    #     index = pinecone.Index(self.connector_config.index_name)
    #     logger.debug(
    #         f"Connected to index: {pinecone.describe_index(self.connector_config.index_name)}"
    #     )
    #     return index

    @DestinationConnectionError.wrap
    @requires_dependencies(["chromadb"], extras="chroma")
    def upsert_batch(self, batch):

        collection = self.chroma_collection

        try:
            print("%%%%%%%%%%%%% Upserting Batch %%%%%%%%%%%%%%")
            # breakpoint()
            # print(batch)
            batch2=self.prepare_chroma_dict(batch)
            print("***** ready batch *****")
            print(batch)
            batch2=aaa
            # Chroma wants lists even if there is only one element
            response = collection.add(ids=batch2["ids"], documents=batch2["documents"], embeddings=batch2["embeddings"], metadatas=batch2["metadatas"])
        except Exception as e:
            raise WriteError(f"chroma error: {e}") from e
        logger.debug(f"results: {response}") # Does this do anything?????


    @staticmethod
    def chunks(iterable, batch_size=1):
        """A helper function to break an iterable into chunks of size batch_size."""
        it = iter(iterable)
        chunk = tuple(itertools.islice(it, batch_size))
        # breakpoint()
        while chunk:
            yield chunk
            chunk = tuple(itertools.islice(it, batch_size))

    @staticmethod
    def prepare_chroma_dict(chunk: t.Tuple[t.Dict[str, t.Any]])-> t.Dict[str, t.List[t.Any]]:
        """Helper function to break a tuple of dicts into list of parallel lists for ChromaDb.
        ({'id':1}, {'id':2}, {'id':3}) -> {'ids':[1,2,3]}"""
        # breakpoint()
        chroma_dict = {}
        chroma_dict["ids"] = [x.get("id") for x in chunk]
        chroma_dict["documents"] = [x.get("document") for x in chunk]
        chroma_dict["embeddings"] = [x.get("embedding") for x in chunk]
        chroma_dict["metadatas"] = [x.get("metadata") for x in chunk]
        assert len(chroma_dict["ids"]) == len(chroma_dict["documents"]) == len(chroma_dict["embeddings"]) == len(chroma_dict["metadatas"])
        # print(chroma_dict)
        return chroma_dict

    def write_dict(self, *args, dict_list: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"Inserting / updating {len(dict_list)} documents to destination "
            # f"index at {self.connector_config.index_name}",
        )

        # this is advised to be 100 at maximum in pinecone docs, however when we
        # chunk content, we hit to the object size limits, so we decrease the batch
        # size even more here

        #THIS IS THE REAL WRITE SPOT. We are not sub batching.
        # pinecone_batch_size = 10

        # num_processes = 1
        # breakpoint()
        if self.write_config.num_processes == 1:
            for chunk in self.chunks(dict_list):# , pinecone_batch_size):
                print(f"len dict list: {len(chunk)}")
                print(chunk)
                # breakpoint()
                # Here we need to parse out the batch into 4 lists (ids, documents, embeddings, metadatas)
                # and also check that the lengths match.
                
                # upsert_batch expects a dict with 4 lists (ids, documents, embeddings, metadatas)
                # breakpoint()
               
                self.upsert_batch(chunk)

                # for i in range(0, len(chunk)):
                #     self.upsert_batch(chunk[i])  

        else:
            print("%%%%%%%%%%%%% Multiprocessing %%%%%%%%%%%%%%")
            with mp.Pool(
                processes=self.write_config.num_processes,
            ) as pool:
                # Prepare the list of lists for multiprocessing
                # pool.map expects a list of dicts with 4 lists (ids, documents, embeddings, metadatas)

                # Prepare the list of chunks for multiprocessing
                # chunk_list = list(self.chunks(self.prepare_chroma_dict(dict_list)))
                ######### this is nor workiing above ^
                # print(f"len chunk list: {len(chunk_list)}")
                # print(chunk_list)
                # Upsert each chunk using multiprocessing
                with mp.Pool(processes=self.write_config.num_processes) as pool:
                    # pool.map(self.upsert_batch, chunk_list)
                    pool.map(self.upsert_batch, list(self.chunks(dict_list)))

    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        dict_list: t.List[t.Dict[str, t.Any]] = []
        for doc in docs:
            local_path = doc._output_filename
            with open(local_path) as json_file:
                dict_content = json.load(json_file)
                # breakpoint()

                # we want a list of dicts that it can upload one at a time.
                # each dict should have documents (aka text), embeddings, metadatas, and ids

                # documents=["This is a document", "This is another document"],
                # metadatas=[{"source": "my_source"}, {"source": "my_source"}],
                # ids=["id1", "id2"]
                # embeddings=[[1,2,3],[4,5,6]]

                # assign element_id and embeddings to "id" and "values"
                # assign everything else to "metadata" field
                dict_content = [
                    {
                        # is element id right id?
                        # "ids": element.pop("element_id", None),
                        "id": str(uuid.uuid4()),
                        "embedding": element.pop("embeddings", None),
                        "document": element.pop("text", None),
                        "metadata": flatten_dict({k: v for k, v in element.items()},separator="-",flatten_lists=True),
                    }
                    for element in dict_content
                ]
                logger.info(
                    f"Extending {len(dict_content)} json elements from content in {local_path}",
                )
                dict_list.extend(dict_content)
                # breakpoint()

                # data={}
                # #### Add type
                # data["ids"]=[x.get("element_id") for x in doc_content]
                # data["documents"]=[x.get("text") for x in doc_content]
                # data["embeddings"]=[x.get("embeddings") for x in doc_content]
                # # flatten this:
                # data["metadatas"]=[flatten_dict(x.get("metadata"),flatten_lists=True) for x in doc_content]


                # assign element_id and embeddings to "id" and "values"
                # assign everything else to "metadata" field
                # dict_content = [
                #     {
                #         "id": element.pop("element_id", None),
                #         "values": element.pop("embeddings", None),
                #         "metadata": {k: json.dumps(v) for k, v in element.items()},
                #     }
                #     for element in dict_content
                # ]
                # logger.info(
                #     f"appending {len(dict_content)} json elements from content in {local_path}",
                # )
                # dict_list.append(data)
        self.write_dict(dict_list=dict_list)



