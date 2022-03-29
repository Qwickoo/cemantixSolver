from flask import Flask, request
from gensim.models import KeyedVectors
import requests

app = Flask(__name__)

class Utils:
    model_url = "https://embeddings.net/embeddings/frWac_non_lem_no_postag_no_phrase_200_cbow_cut100.bin"
    # model_url = "data/frWac_non_lem_no_postag_no_phrase_200_cbow_cut100.bin"
    loading = False
    today_s_word = ''
    tried = 0


    def reset():
        Utils.loading = True
        Utils.today_s_word = ''
        Utils.tried = 0


    def guess(word):
        Utils.tried += 1
        req = requests.post('https://cemantix.herokuapp.com/score', data = {'word': word}).json()
        if 'score' in req:
            return req['score']
        
        return -1000


    def computeEcart(score_1, score_2):
        return abs(score_1 - score_2)


    def mapToList(mapContainer):
        return map(lambda l: l['word'], mapContainer)


    def isWordWorthToTry(word_tried, model, word, difference_to_test):
        word_worth_try = True
        total_similarity = 0

        for index in range(len(word_tried)):
            similarity = model.similarity(word, word_tried[index]['word'])
            ecart = Utils.computeEcart(similarity, word_tried[index]['guess'])
            total_similarity += ecart

            if ecart > difference_to_test:
                word_worth_try = False
                break

        return word_worth_try, total_similarity


    def findTodaysWord(starter, model):
        starter_guess = Utils.guess(starter)
        word_tried = [{'word': starter, 'guess': starter_guess}]
        word_denied = []
        word_found = ''

        difference_to_test = 0.005
        while word_found == '':
            words_worth_to_try = []
            print(f"Testing with difference {difference_to_test} for words {word_tried}")

            for word in model.index_to_key :
                if word not in Utils.mapToList(word_tried) and word not in word_denied and not word.endswith('es') and not word.endswith('ée') and not word.endswith('eaux'):
                    word_worth_to_try, total_similarity = Utils.isWordWorthToTry(word_tried, model, word, difference_to_test)
                    if word_worth_to_try:
                        words_worth_to_try.append({'word': word, 'total': total_similarity})

            if len(words_worth_to_try) > 0:
                word = sorted(words_worth_to_try, key=lambda w: w['total'])[0]['word']

                guess = Utils.guess(word)
                if guess != -1000:
                    word_tried.append({'word': word, 'guess': guess})
                    print(f"Word may be {word} : {guess}")

                    if guess > 0.99:
                        word_found = word
                        break

                    if guess > 0.2:
                        if len(list(filter(lambda l: l['guess'] > 0.2, word_tried))) > 0:
                            word_tried = list(filter(lambda l: l['guess'] > 0.2, word_tried))
                                
                    difference_to_test = 0.001
                else:
                    word_denied.append(word)
                    

            difference_to_test *= 2

        print(word_denied)

        return word_found


    def initForNewDay(starter):
        print("Initializing for new day")
        Utils.reset()

        print("Loading model")
        model = KeyedVectors.load_word2vec_format(Utils.model_url, binary=True, unicode_errors="ignore")

        Utils.today_s_word = Utils.findTodaysWord(starter, model)
        Utils.loading = False
        return Utils.today_s_word

@app.route('/init', methods=['GET'])
def init():
    args = request.args
    return Utils.initForNewDay(args.get("starter"))

@app.route('/', methods=['GET'])
def nospoil():
    if Utils.today_s_word == '':
        return f"App is loading, please wait a sec. (Current attempts : {Utils.tried})"
    else:
        return {
            'word': 'found ! Go to /spoil to get spoiled',
            'attempts': Utils.tried
        }

@app.route('/spoil', methods=['GET'])
def spoil():
    if Utils.today_s_word == '':
        return f"App is loading, please wait a sec. (Current attempts : {Utils.tried})"
    else:
        return {
            'word': Utils.today_s_word,
            'attempts': Utils.tried
        }


