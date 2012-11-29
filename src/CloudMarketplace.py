""" This is a basic simulation of consumer-producer market model using the
SimPY library. """

'''

TODO:
 * consider a consumer motivated by time, or deadline (optional?) 
   * this requires the incorporation of a consumer deadline and different
   * clearly, a minimal time chooses machine with most capacity
 * consider consumer utilization % (assumer 100% now)
 * Monitoring / Data collection on consumers, resources
   - total money spent
   - total work done
   - income to provider
   - average job cost
   - average job length
   - average price per unit

 * wrap your head about how simulation steps relate to time.
   - a simulation step can represent anything: secs -> mins -> hours
   - time-per-step ratio should be global
   - time-per-step must be <= min unit time

'''
import math
from SimPy.Simulation import *

# Props ##################################################################### 

class Unit():
  """ compute unit - capacity over time """
  def __init__(self, capacity, time, cost):
    self.capacity = capacity  # work capacity (CPU throughput)
    self.time  = time         # the number of simulation steps a unit costs " 
    self.cost  = cost         # base (on-demand) cost of unit 

class Lease():
  """ lease duration and costs """
  """ on-demand instances have a zero length and down payment """
  def __init__(self, length, downp, puc):
    self.length = length  # required length (0 = no limit)
    self.downp = downp    # down payment
    self.puc = puc        # percentage unit cost

class Instance(): 
  """ an compute instance """
  def __init__(self, name, desc, unit, lease):
    self.name = name
    self.desc = desc
    self.unit = unit       # unit classes
    self.lease = lease     # package class
    self.invoked = 0       # statistics
    self.income = 0
    self.work = 0
    self.time = 0
    self.unused = 0

  """
  we are given a requested amount of work.  Return the work completed, work
  remaining, total cost and efficiency for this instance 
  """
  def analyize(self, work):
    # partial units consumed are billed as a full unit 
    req_units = math.ceil(work / self.unit.capacity) # requested units
    max_units = math.floor(self.lease.length / self.unit.time)  
    rmdr = 0 # remaning work
    rtime = 0 # remaining time on lease
    """ on-demand leases have a zero length """
    if (self.lease.length > 0):
      """ a fixed lease can processes limited number of units"""
      if (req_units > max_units): #we need more work than lease allows
        req_units = max_units
        rmdr = work - (max_units * self.unit.capacity)
        work = max_units * self.unit.capacity
      # endif
      rtime = self.lease.length - (req_units * self.unit.time)
    #endif
    cost =  self.lease.downp + (req_units * (self.unit.cost * self.lease.puc))
    time = req_units * self.unit.time
    rate = work / cost
    cpr = work / cost / time # instance efficency 
    print ">", self.desc,":",cpr, rtime
    return {'cost': cost, 'time': time, 'work':work, 'rmdr': rmdr,
        'rate':rate, 'cpr':cpr, 'rtime':rtime}
  
  """ list the data for instance """
  def results(self):
    return [self.invoked, self.desc, self.unit.capacity, self.unit.time, \
        self.unit.cost, self.lease.puc, (self.unit.cost * self.lease.puc),\
        self.lease.length, self.lease.downp] 
    
## actors  ########################################################### 

class Consumer(Process):
  """ a basic consumer motivated by overall cost """
  def __init__(self, name, work, start, sim):
    Process.__init__(self, name=name, sim=sim)
    self.work =  work
    self.rmdr =  work
    self.start = start
    self.spent = 0
    self.finish = 0
    self.rtime = 0

  """ search list for best cost efficiency, i.e, most work per dollar  """
  def shop_for_cpr(self, work, instance_list):
    prev = 0
    for inst in instance_list: 
      data = inst.analyize(work) # get instance report for data
      tmp = data['cpr'] 
      if tmp >= prev or prev == 0:
        prev = tmp
        rtn = data
        rtn['inst'] = inst
    return rtn

  """ purchase resource based on the results of financial analysis """
  def purchase(self, work, instance_list):
    """ shop for the highest cost effectivness """
    rtn = self.shop_for_cpr(work, instance_list)
    print self.name," PURCHASED:", rtn['inst'].desc, rtn['cost'],rtn['cpr'], rtn['rtime']
    """ update simulation statistics """
    self.sim.income += rtn['cost']
    rtn['inst'].invoked += 1
    rtn['inst'].income += rtn['cost']
    rtn['inst'].work +=   rtn['work']
    rtn['inst'].time +=   rtn['time']
    rtn['inst'].unused += rtn['rtime']
    self.spent += rtn['cost']
    self.rtime += rtn['rtime']
    self.rmdr = rtn['rmdr']
    return rtn

  """ process work by purchasing instances """
  def process(self):
    while self.rmdr > 0:
      data = self.purchase(self.rmdr, self.sim.instances)
      yield hold, self, data['time']
    self.finish = self.sim.now()

  def results(self):
    """ return consumer data list """
    time = self.finish - self.start # total time
    return [self.name, self.work, self.spent, time, self.start, self.finish,
        self.rtime] 


## stage ############################################################# 

class Marketplace(Simulation):
  def __init__(self, name, instances, consumers, maxtime=100000000):
    Simulation.__init__(self)
    self.name = name
    self.instances = instances 
    self.consumer_specs = consumers
    self.consumer_count = len(consumers['work'])
    self.maxtime = maxtime
    self.consumers = []
    self.income = 0
    self.finished = 0 # jobs completed 

  def spawn_consumers(self, specs):
    """ spawn and activate consumers for simulation """
    for i in range(len(specs['work'])):
      con = Consumer(name="con_%s"%i, work=specs['work'][i], \
          start=specs['start_time'][i], sim=self)
      self.consumers.append(con)
      self.activate(con, con.process(), at=con.start)

  def start(self):
    self.initialize()
    print self.now(), ':', self.name, 'started',self.consumer_count,'consumers'
    self.spawn_consumers(self.consumer_specs)
    self.simulate(until=self.maxtime)

  def finish(self):
    print self.now(), ':', self.name, 'finished.'

  def results_primary(self):
    print "Primary Market Stats"

  def results_inst(self):
    return_list = []
    for inst in self.instances:
      return_list.append(inst.results())
    return return_list

  def results_cons(self):
    return_set = {'name':[],'work':[],'cost':[], 'time':[],
        'start':[],'finish':[]}
    for cons in self.consumers:
      i = cons.results()
      return_set['name'].append(i[0])
      return_set['work'].append(i[1])
      return_set['cost'].append(i[2])
      return_set['time'].append(i[3])
      return_set['start'].append(i[4])
      return_set['finish'].append(i[5])
    return return_set
# fin.
