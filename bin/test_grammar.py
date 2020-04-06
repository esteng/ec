try:
    import binutil  # required to import from dreamcoder modules
except ModuleNotFoundError:
    import bin.binutil  # alt import if called as module

from dreamcoder.grammar import *
from dreamcoder.domains.arithmetic.arithmeticPrimitives import *
from dreamcoder.domains.list.listPrimitives import *
from dreamcoder.program import Program
from dreamcoder.valueHead import *
from dreamcoder.zipper import *

from dreamcoder.domains.tower.towerPrimitives import *

bootstrapTarget()
g = Grammar.uniform([k0,k1,addition, subtraction, Program.parse('cons'), 
    Program.parse('car'), Program.parse('cdr'), Program.parse('empty'),
    Program.parse('fold'), Program.parse('empty?')])

#g = g.randomWeights(lambda *a: random.random())
#p = Program.parse("(lambda (+ 1 $0))")
request = arrow(tint,tint)

def testEnumWithHoles():
    i = 0
    for ll,_,p in g.enumeration(Context.EMPTY,[],request,
                               6.,
                               enumerateHoles=True):

        i+=1
        if i==4:
            print("ref sketch", p)
            break

    for ll,_,pp in g.sketchEnumeration(Context.EMPTY,[],request, p,
                               6.,
                               enumerateHoles=True):
        print(pp)

        #ll_ = g.logLikelihood(request,p)
        #print(ll,p,ll_)
        #d = abs(ll - ll_)
        #assert d < 0.0001

def testSampleWithHoles():

    for _ in range(1000):
        p = g.sample(request, maximumDepth=6, maxAttempts=None, sampleHoleProb=.2)
        print(p, p.hasHoles)

        print("a sample from the sketch")
        print("\t", g.sampleFromSketch( request, p, sampleHoleProb=.2))

def findError():
    p = Program.parse('(lambda (fold <HOLE> 0 (lambda (lambda (+ $1 $0)) )))')
    for i in range(100):
        print("\t", g.sampleFromSketch( request, p, sampleHoleProb=.2))

def test_training_stuff():
    p = g.sample(request)
    print(p)

    for x in sketchesFromProgram(p, request, g):
        print(x)

def test_getTrace():
    full = g.sample(request)
    print("full:")
    print('\t', full)
    trace, negTrace= getTracesFromProg(full, request, g, onlyPos=False)
    print("trace:", *trace, sep='\n\t')
    #assert [full == p.betaNormalForm() trace]
    print("negTrace", *negTrace, sep='\n\t')

    assert trace[-1] == full
    return full


def test_sampleOneStep():
    for i in range(100):
        subtree = g._sampleOneStep(request, Context.EMPTY, [])
        print(subtree)

def test_holeFinder():

    #p = Program.parse('(lambda (fold <HOLE> 0 (lambda (lambda (+ $1 $0)) )))')
    for i in range(100):
        expr = g.sample( request, sampleHoleProb=.2)
        


    expr = Program.parse('(empty? (cons <HOLE> <HOLE>))')
    print("\t", expr )

    print([(subtree.path, subtree.tp, subtree.env) for subtree in findHolesEnum(tbool, expr)])
    #print([(subtree.path, subtree.env) for subtree in findHoles(expr, request)])

def test_sampleSingleStep():

    nxt = baseHoleOfType(request)
    zippers = findHoles(nxt, request)
    print(nxt)

    while zippers:
        nxt, zippers = sampleSingleStep(g, nxt, request, holeZippers=zippers)
        print(nxt)

def test_SingleStep1():

    #request = tbool
    #expr = Program.parse('(empty? (cons <HOLE> <HOLE>))')
    expr = Program.parse('(lambda (fold <HOLE> 0 (lambda (lambda (+ $1 $0)) )))')

    nxt, zippers = sampleSingleStep(g, expr, request)

    print(nxt)
    #print([(subtree.path, subtree.tp, subtree.env) for subtree in zippers])
    print(zippers)



# request = arrow(tint, tint)
# i = 0
# for ll,_,p in g.enumeration(Context.EMPTY,[],request,
#                            12.,
#                            enumerateHoles=False):


#     print(i, p)
#     #if i==7: break
#     i+=1

def test_abstractHoles():

    #g = Grammar.uniform([k0,k1,addition, subtraction])
    bootstrapTarget_extra()
    expr = g.sample( request, sampleHoleProb=.2)
    expr = Program.parse('(lambda (map (lambda <HOLE>) $0))')
    #expr = Program.parse('(lambda (map (lambda (+ $0 17111)) (map (lambda <HOLE>) $0)))')
    #expr = Program.parse('(lambda (map (lambda (+ $0 1)) (map (lambda <HOLE>) $0)))')
    expr = Program.parse('(lambda (map (lambda (is-square $0)) $0))')

    #expr = Program.parse('(lambda (map (lambda 3) $0))')
    print("expr:", expr)

    p = expr.evaluate([])
    print("eval:", p([4,3,1]))


def test_abstractREPL():
    from dreamcoder.domains.list.makeListTasks import make_list_bootstrap_tasks
    from dreamcoder.domains.list.main import LearnedFeatureExtractor
    tasks = make_list_bootstrap_tasks()
    cuda = True

    featureExtractor = LearnedFeatureExtractor(tasks, testingTasks=tasks[-3:], cuda=cuda)
    valueHead = AbstractREPLValueHead(g, featureExtractor, H=64)

    sketch = Program.parse('(lambda (map (lambda <HOLE>) $0))')
    #print(tasks[2])
    task = tasks[2]
    task.examples = task.examples[:1] 
    print(task.examples)
    valueHead.computeValue(sketch, task)

def test_trainAbstractREPL():
    from dreamcoder.domains.list.makeListTasks import make_list_bootstrap_tasks
    from dreamcoder.domains.list.main import LearnedFeatureExtractor
    tasks = make_list_bootstrap_tasks()
    cuda = True

    TASKID = 3

    import dill
    with open('testFrontier.pickle', 'rb') as h:
        lst = dill.load(h)

    # for i, (frontier, g) in enumerate(lst):
    #     if i == TASKID:
    #         print(i)
    #         print(frontier.task.examples)
    #         print(frontier.sample().program._fullProg)

    frontier, g = lst[TASKID]

    featureExtractor = LearnedFeatureExtractor(tasks, testingTasks=tasks[-3:], cuda=cuda)
    valueHead = AbstractREPLValueHead(g, featureExtractor, H=64)
    #valueHead = SimpleRNNValueHead(g, featureExtractor, H=64)

    print(frontier.task.examples)
    print(frontier.sample().program._fullProg)
    optimizer = torch.optim.Adam(valueHead.parameters(), lr=0.001, eps=1e-3, amsgrad=True)

    for i in range(400):
        valueHead.zero_grad()

        
        losses = [valueHead.valueLossFromFrontier(frontier, g) for frontier, g in lst]
        loss = sum(losses)
        print(loss.data.item())
        loss.backward()
        optimizer.step()

def test_abstractHolesTower():

    #g = Grammar.uniform([k0,k1,addition, subtraction])
    # bootstrapTarget_extra()

    #expr = g.sample( request, sampleHoleProb=.2)
    #expr = Program.parse('(lambda (map (lambda <HOLE>) $0))')
    #expr = Program.parse('(lambda (map (lambda (+ $0 17111)) (map (lambda <HOLE>) $0)))')
    #expr = Program.parse('(lambda (map (lambda (+ $0 1)) (map (lambda <HOLE>) $0)))')
    # expr = Program.parse('(lambda (map (lambda (is-square $0)) $0))')
    

    def _empty_tower(h): return (h,[])

    
    expr = Program.parse('(lambda (tower_loopM <HOLE> (lambda (lambda (moveHand 3 (3x1 $0)))) <TowerHOLE>)) ') 
    #expr = Program.parse('(lambda (tower_loopM 3 (lambda (lambda (moveHand 3 (3x1 $0)))) <TowerHOLE>)) ') 

    #expr = Program.parse('(lambda (tower_loopM 3 (lambda (lambda <TowerHOLE>)) <TowerHOLE>)) ') 
    #expr = Program.parse('(lambda (3x1 (1x3 $0) ))') 

    #expr = Program.parse('(lambda (3x1 (1x3 <TowerHOLE>) ))') 
    expr = Program.parse('(lambda (1x3 (moveHand <HOLE> (reverseHand <TowerHOLE>))) )') 
    expr = Program.parse('(lambda (1x3 (moveHand <HOLE> (reverseHand <TowerHOLE>))) )') 
    #expr = Program.parse('(lambda (<TowerHOLE>) )') 
    expr = Program.parse('(lambda (tower_loopM <HOLE> (lambda (lambda <TowerHOLE>)) <TowerHOLE>))')
    #animateTower('test', expr)

    x = expr.evaluateHolesDebug([])(_empty_tower)(TowerState(history=[])) #can initialize tower state with 
    print(x)
    

def test_abstractHolesTowerValue():


    def _empty_tower(h): return (h,[])

    
    expr = Program.parse('(lambda (tower_loopM <HOLE> (lambda (lambda (moveHand 3 (3x1 $0)))) <TowerHOLE>)) ') 
 
    expr = Program.parse('(lambda (1x3 (moveHand <HOLE> (reverseHand <TowerHOLE>))) )') 
    expr = Program.parse('(lambda (1x3 (moveHand <HOLE> (reverseHand <TowerHOLE>))) )') 
    #expr = Program.parse('(lambda (<TowerHOLE>) )') 
    expr = Program.parse('(lambda (tower_loopM <HOLE> (lambda (lambda <TowerHOLE>)) <TowerHOLE>))')
    #animateTower('test', expr)
        
    x = expr.evaluateHolesDebug([])(_empty_tower)(TowerState(history=[])) #can initialize tower state with 
    print(x)

if __name__=='__main__':
    #findError()
    #testSampleWithHoles()
    #test_training_stuff()
    #test_holeFinder()
    #full = test_getTrace()
    #test_sampleOneStep()
    #test_sampleSingleStep()
    #test_SingleStep1()
    #test_abstractHoles()
    #test_abstractREPL()
    # test_trainAbstractREPL()
    # bootstrapTarget_extra()
    # from dreamcoder.domains.list.makeListTasks import make_list_bootstrap_tasks
    # from dreamcoder.domains.list.main import LearnedFeatureExtractor
    # tasks = make_list_bootstrap_tasks()
    # expr = Program.parse('(lambda (map (lambda (is-square $0)) $0))')
    test_abstractHolesTower()