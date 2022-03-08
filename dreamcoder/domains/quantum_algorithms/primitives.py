import numpy as np
import dreamcoder as dc
from dreamcoder.utilities import eprint

try:
    import qiskit as qk
    from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit,Aer
    backend = Aer.get_backend('unitary_simulator')
except:
    eprint("Qiskit not found. Necessary for quantum circuit plots.")
# ------------------------------------------
# Define functions that operate on unitaries
# (written as tensors)


def mat_to_tensor(mat):
    n_qubits = int(np.math.log2(mat.shape[0]))
    return mat.reshape([2]*n_qubits*2)
    # first qubits are output, last qubits are input


def get_qubit_number(tensor):
    return int(len(tensor.shape)/2)


def tensor_to_mat(tensor):
    dim_space = 2**get_qubit_number(tensor)
    return tensor.reshape([dim_space, dim_space])


def tensor_product(A, B):
    shape = A.shape[-1]*B.shape[-1]
    return np.reshape(A[..., :, None, :, None]*B[..., None, :, None, :], (-1, shape, shape))


def tensor_contraction(A, B, indices):
    n_qubits = get_qubit_number(A)
    idx = [i + n_qubits for i in indices]
    out = np.tensordot(A, B, (idx, np.arange(len(indices))))
    return np.moveaxis(out, np.arange(-len(indices), 0, 1), idx)

# not really needed, just for completeness


def mat_contraction(A, B, indices):
    return tensor_to_mat(tensor_contraction(
        mat_to_tensor(A),
        mat_to_tensor(B),
        indices)
    )

# ------------------------------------------
# Some simple gates
#

mat_cnot = np.array([[1,0,0,0],
                     [0,1,0,0],
                     [0,0,0,1],
                     [0,0,1,0]])
tensor_cnot = mat_to_tensor(mat_cnot)

mat_swap = np.array([[1,0,0,0],
                     [0,0,1,0],
                     [0,1,0,0],
                     [0,0,0,1]])
tensor_swap = mat_to_tensor(mat_swap)


mat_hadamard = np.array([[1,1],
                         [1,-1]])/np.sqrt(2)
tensor_hadamard = mat_to_tensor(mat_hadamard)

mat_cz = np.array([[1,0,0,0],
                     [0,1,0,0],
                     [0,0,1,0],
                     [0,0,0,-1]])
tensor_cz = mat_to_tensor(mat_cz)

# ------------------------------------------
# Apply a gate on all given qubits
#
def eye(n):
    return mat_to_tensor(np.eye(2**n))


def hadamard(circuit, qubit_1):
    return tensor_contraction(circuit, tensor_hadamard, [qubit_1])


def cnot(circuit, qubit_1, qubit_2):
    return tensor_contraction(circuit, tensor_cnot, [qubit_1, qubit_2])


def swap(circuit, qubit_1, qubit_2):
    return tensor_contraction(circuit, tensor_swap, [qubit_1, qubit_2])


def cz(circuit, qubit_1, qubit_2):
    return tensor_contraction(circuit, tensor_cz, [qubit_1, qubit_2])


# ------------------------------------------
# Transform a list of qubit operations into a unitary 
#
full_op_names = {
    "eye": eye,
    "hadamard": hadamard,
    "cnot": cnot,
    "swap": swap,
    "cz": cz
}

qiskit_full_op_names = lambda QT: {
    "eye": lambda q1: QT.circuit.id(QT.q(q1)),
    "hadamard": lambda q1: QT.circuit.h(QT.q(q1)),
    "cnot":  lambda q1,q2: QT.circuit.cnot(QT.q(q1),QT.q(q2)),
    "swap": lambda q1,q2: QT.circuit.swap(QT.q(q1),QT.q(q2)),
    "cz": lambda q1,q2: QT.circuit.cz(QT.q(q1),QT.q(q2)),
}

def full_circuit_to_mat(full_circuit):
    n_qubit, op_list = full_circuit
    
    tensor = eye(n_qubit)
    for op in op_list:
        tensor = full_op_names[op[0]](tensor, *op[1:])
        
    return tensor_to_mat(tensor)

def state_circuit_to_mat(circuit):
    return full_circuit_to_mat([circuit[0][-1], circuit[1]])
    
## Qiskit implementation, which natively also includes plotting 
class QiskitTester():
    def __init__(self,unitary_tensor):
        self.unitary_tensor = unitary_tensor
        self.unitary_matrix = tensor_to_mat(unitary_tensor)
        self.n_qubits = get_qubit_number(self.unitary_tensor)
        self.qreg_q = QuantumRegister(self.n_qubits, 'q')
        self.circuit = QuantumCircuit(self.qreg_q)
        
    def q(self,q_num):
        return self.n_qubits -1- q_num
    
    def __enter__(self):
        return self
    
    def __exit__(self,*args, **kwargs):
        self.result = np.array(qk.execute(self.circuit, backend).result().get_unitary()).T
        try:
            np.testing.assert_almost_equal(self.unitary_matrix,self.result, decimal=5)
            print("Code consistent with Qiskit")
        except AssertionError as e:
            print("-----------------------------------")
            print("ERROR: ")
            print(self.unitary_matrix)
            print(self.result)
            print(e)





# ------------------------------------------
# Define functions for primitives (to act on circuits)
# 
POS = 0
DIR = 1
N = 2

DIR_NEXT = 1
DIR_PREV = -1
STATE_0 = lambda n_qubits: [0,DIR_NEXT,n_qubits]

# State operations
def _change_direction(old_circuit):
    state, circuit = old_circuit
    state[DIR] *= -1
    return [state, circuit]

def _move_next(old_circuit):
    state, circuit = old_circuit
    if state[POS] >=state[N]-1:
        raise Exception("Invalid selected qubit")
    
    state[POS] += 1
    return [state, circuit]

def _move_prev(old_circuit):
    state, circuit = old_circuit
    if state[POS] <=0:
        raise Exception("Invalid selected qubit")
        
    state[POS] -= 1
    return [state, circuit]


# Circuit operation
def _no_op(n):
    return [STATE_0(n), []]

def _hadamard(old_circuit):
    state, circuit = old_circuit
    circuit.append( ["hadamard", state[POS]])
    return [state, circuit]

def _cnot(old_circuit):
    state, circuit = old_circuit
    
    second_qubit =  state[POS]+state[DIR]
    if second_qubit<0 or second_qubit >= state[N]:
        raise Exception("Invalid selected qubit")
    
    circuit.append(["cnot", state[POS], second_qubit])
    return [state, circuit]

# Control
def _repeat(n_times,body):
    if n_times <= 0:
        raise Exception("Invalid repetition number.")
    return   _repeat_help(n_times, body, body)

def _repeat_help(n_times, body, new_body):
    if n_times==1:
        return new_body
    return _repeat_help(n_times-1, body, lambda b: new_body(body(b)))


# ------------------------------------------
# Define TYPES
# 
tsize = dc.type.baseType("tsize")
tcircuit = dc.type.baseType("tcircuit")

# ------------------------------------------
# Define PRIMITIVES
# 

# State primitives
p_move_next = dc.program.Primitive(name="mv", 
                     ty=dc.type.arrow(tcircuit, tcircuit),
                     value=_move_next)

p_move_prev = dc.program.Primitive(name="mv_r", 
                     ty=dc.type.arrow(tcircuit, tcircuit),
                     value=_move_prev)

p_change_direction = dc.program.Primitive(name="minv", 
                     ty=dc.type.arrow(tcircuit, tcircuit),
                     value=_change_direction)

# Circuit primitives
p_no_op = dc.program.Primitive(name="no_op", 
                     ty=dc.type.arrow(tsize, tcircuit),
                     value=_no_op)

p_hadamard = dc.program.Primitive(name="h", 
                     ty=dc.type.arrow(tcircuit, tcircuit),
                     value=_hadamard)

p_cnot = dc.program.Primitive(name="cnot", 
                     ty=dc.type.arrow(tcircuit,tcircuit),
                     value=_cnot)

# Control
p_iteration = dc.program.Primitive(name="rep", 
                     ty=dc.type.arrow(dc.type.tint, dc.type.arrow(tcircuit,tcircuit),  dc.type.arrow(tcircuit,tcircuit)),
                     value=dc.utilities.Curried(_repeat))

# Arithmetics
p_0 = dc.program.Primitive("0",dc.type.tint,0)
p_inc = dc.program.Primitive("inc", dc.type.arrow(dc.type.tint, dc.type.tint), lambda x:x+1)
p_dec = dc.program.Primitive("dec", dc.type.arrow(dc.type.tint, dc.type.tint), lambda x:x-1)
p_cast_size_to_int = dc.program.Primitive("size_to_int", dc.type.arrow(tsize, dc.type.tint), lambda x:x)


primitives = [
    #states
    p_move_next,
    p_move_prev,
    p_change_direction,
    #circuits
    p_no_op,
    p_hadamard,
    p_cnot,
    #control
    p_iteration,
    #arithmetics
    p_0,
    p_inc,
    p_dec,
    p_cast_size_to_int
]


# ------------------------------------------
# Define GRAMMAR
# 
grammar = dc.grammar.Grammar.uniform(primitives)
            


# ------------------------------------------
# Function to execute algorithms (which are functions)
# Maybe it should return a function?
# 
def execute_quantum_algorithm(p, n_qubits, timeout=None):
    try:
        circuit =  dc.utilities.runWithTimeout(
            lambda: p.evaluate([])(n_qubits),
            timeout=timeout
        )
        return state_circuit_to_mat(circuit)
    except dc.utilities.RunWithTimeout: return None
    except: return None
    
    
