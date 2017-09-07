import cmath
import numpy as np
import matplotlib.pyplot as plt

#make net_circulation as an attribute
#utility functions

def dot(a,b):
    return a.real*b.real + a.imag*b.imag

class Vortex(object):

    def __init__(self, location, circulation, fixed=False, reflection=False, original=False):
        '''
        Location should be a complex number
        '''
        self.location = location    
        self.circulation = circulation
        self.fixed = fixed
        self.path = [location]
        self.step = complex(0,0)
        self.reflection = reflection
        self.original = original


    def potential(self, location):
        '''
        Returns a complex potential at a given location
        '''

        return (complex(0,-1)*(cmath.log(location - self.location))*(self.circulation)/(2*cmath.pi))

    def potential_grad(self, location):
        '''
        Returns a complex gradient of the potential function at a given location
        '''

        return (complex(0,-1)*self.circulation/(2*cmath.pi))*(1/(location - self.location))

    def get_velocity(self, location):

        return complex(self.potential_grad(location).real,(-1*(self.potential_grad(location).imag)))

    def get_krasny_velocity(self, location, delta):
        relative_vector = location - self.location
        mod = abs(relative_vector)
        conj = relative_vector.conjugate()
        modified_grad = (complex(0,-1)*self.circulation/(2*cmath.pi))*(conj)*(1/abs(mod**2 + delta**2))
        return complex(modified_grad.real,(-1*(modified_grad.imag)))

class Cont_panel(object):

    def __init__(self, points, velocity=0):
        self.panel_points = [Panel_point(points[i],0,i) for i in range(len(points))]
        self.velocity = velocity

    def get_velocity(self, location):
        res = 0
        for i in range(len(self.panel_points) - 1):
            p1 = self.panel_points[i]
            p2 = self.panel_points[i+1]
            relative_vector = p2.location - p1.location
            t = (relative_vector)/abs(relative_vector)
            tc = t.conjugate()
            z = (location - p1.location)*tc
            uiv = (1j*p1.gamma*cmath.log(1-(abs(relative_vector)/z)))/(2*cmath.pi)
            uiv = uiv.conjugate()
            uiv = uiv*t
            res += uiv
        return res

    def solve(self, net_circulation, system):
        for i in self.panel_points:
            i.gamma = 0
        A = []
        b = []
        lambdas = []
        for k in range(len(self.panel_points) - 1):
            p1 = self.panel_points[k]
            p2 = self.panel_points[k+1]
            midpoint = (p1.location + p2.location)/2
            relative_vector = p2.location - p1.location
            lambdas.append(abs(relative_vector))
            t = (relative_vector)/abs(relative_vector)
            n = 1j*t
            v = 0
            # ought to generalize this
            if system.freestreams is not None:

                for freestream in system.freestreams:
                    v += freestream.get_velocity(midpoint)
            if system.vortices is not None:
                for vortex in system.vortices:
                    v += vortex.get_velocity(midpoint)
            b.append(dot(n, self.velocity -v))
            a = []
            for m in range(len(self.panel_points) - 1):
                z1 = self.panel_points[m]
                z2 = self.panel_points[m+1]
                relative_vector_z = z2.location - z1.location
                tz = (relative_vector_z)/abs(relative_vector_z)
                tzc = tz.conjugate()
                z = (midpoint - z1.location)*tzc
                coeff = (1j*cmath.log(1-(abs(relative_vector_z)/z)))/(2*cmath.pi)
                coeff = coeff.conjugate()
                coeff = coeff*tz
                coeff = dot(n, coeff)
                a.append(coeff)
            A.append(a)
        A.append(lambdas)
        b.append(net_circulation)
        self.A = A
        self.b = b
        sol = np.linalg.lstsq(np.array(A), np.array(b))[0]
        for i in range(len(self.panel_points)-1):
            self.panel_points[i].gamma = sol[i]

class Panel_point(object):

    def __init__(self, location, gamma, number):

        self.location = location
        self.gamma = gamma
        self.number = number

class Linear_panel(object):
    '''
    A collection of points forming a circle with a gamma value for each.

    '''

    def __init__(self, points, velocity=0):
        '''
        n is the number of panels
        r is the radius of the circle
        '''
        self.panel_points = [Panel_point(points[i],0,i) for i in range(len(points))]
        self.velocity = velocity
        self.n = len(self.panel_points)
    def get_velocity(self, location):

        res_final = 0
        for i in range(self.n - 1):
            p1 = self.panel_points[i]
            p2 = self.panel_points[i+1]
            rel = p2.location - p1.location
            lamda = abs(rel)
            t = rel/lamda
            tc = t.conjugate()
            z = (location - p1.location)*tc
            res =  (-1j*p1.gamma/(2*cmath.pi))*((((z/lamda)-1)*cmath.log(1-(lamda/z)))+1) +\
             (1j*p2.gamma/(2*cmath.pi))*((((z/lamda))*cmath.log(1-(lamda/z)))+1)
            res = res.conjugate()
            res = res*t
            #rotate
            res_final += res
        return res_final

    def solve(self, net_circulation, system):
        for i in self.panel_points:
            i.gamma = 0
        A = map(list,np.zeros((self.n - 1, self.n)))
        b = []
        lambdas = list(np.zeros(self.n))

        for k in range(self.n - 1):
            p1 = self.panel_points[k]
            p2 = self.panel_points[k+1]
            midpoint = (p1.location + p2.location)/2
            relative_vector = p2.location - p1.location
            lambdas[k] += abs(relative_vector)/2
            lambdas[k+1] += abs(relative_vector)/2
            t = (relative_vector)/abs(relative_vector)
            n = 1j*t
            v = 0
            #ought to generalize this
            if system.freestreams is not None:

                for freestream in system.freestreams:
                    v += freestream.get_velocity(midpoint)
            if system.vortices is not None:
                for vortex in system.vortices:
                    v += vortex.get_velocity(midpoint)
            b.append(dot(n, self.velocity -v))
            for m in range(self.n - 1):
                z1 = self.panel_points[m]
                z2 = self.panel_points[m+1]
                rel = z2.location - z1.location
                lamda = abs(rel)
                tz = rel/lamda
                tc = tz.conjugate()
                z = (midpoint - z1.location)*tc
                res1 = (-1j/(2*cmath.pi))*((((z/lamda)-1)*cmath.log(1-(lamda/z)))+1)

                res2 = (1j/(2*cmath.pi))*((((z/lamda))*cmath.log(1-(lamda/z)))+1)
                res1 = res1.conjugate()*tz
                res2 = res2.conjugate()*tz
                A[k][m] += dot(n,res1)
                A[k][m+1] += dot(n,res2)
        A.append(lambdas)
        b.append(net_circulation)
        self.A = np.array(A)
        self.b = np.array(b)
        sol = np.linalg.lstsq(np.array(A), np.array(b))[0]
        for i in range(len(self.panel_points)):
            self.panel_points[i].gamma = sol[i]


class Source(object):

    def __init__(self, location, strength, fixed=True):
        '''
        Location should be a complex number
        '''
        self.location = location
        self.strength = strength
        self.fixed = fixed
        self.fixed = fixed
        self.path = [location]
        self.step = complex(0,0)

    def potential(self, location):
        '''
        Returns a complex potential at a given location
        '''

        return ((cmath.log(location - self.location))*(self.strength)/(2*cmath.pi))

    def potential_grad(self, location):
        '''
        Returns a complex gradient of the potential function at a given location
        '''

        return (self.strength/(2*cmath.pi))*(1/(location - self.location))

    def get_velocity(self, location):

        return complex(self.potential_grad(location).real,(-1*(self.potential_grad(location).imag)))

class Doublet(object):

    def __init__(self, u, position):
        self.u = u
        self.position = position

    def potential(self, location):

        return (-1*self.u)/(2*cmath.pi*(location- self.position))

    def potential_grad(self, location):

        return (self.u)/((2*cmath.pi*((location - self.position)**2)))

    def get_velocity(self, location):

        return complex(self.potential_grad(location).real,(-1*(self.potential_grad(location).imag)))

class Freestream(object):

    def __init__(self, velocity, fixed=True):
        '''
        Velocity should be a complex number
        '''
        self.velocity = velocity
        self.fixed = fixed

    def potential(self, location):
        '''
        Returns a complex potential at a given location
        '''

        return (self.velocity*location)

    def potential_grad(self, location):
        '''
        Returns a complex gradient of the potential function at a given location
        '''

        return complex(self.velocity)

    def get_velocity(self, location):
        # is this correct?
        return complex(self.potential_grad(location).real,(-1*(self.potential_grad(location).imag)))

class Tracer(object):

    def __init__(self, location):
        '''
        Location should be a complex number
        '''
        self.location = location
        self.path = [location]
        self.step = complex(0,0)

class Setup(object):

    def __init__(self, assignment_panel=False,sources=None, vortices=None, freestreams=None, tracers=None, cont_panels=None, doublets=None, linear_panels=None):
        '''
        each kwarg should be a list of respective object,
        tracers is a list containing initial coordinates of each tracer
        '''
        self.sources = sources
        self.vortices = vortices
        self.freestreams = freestreams
        self.tracers = tracers
        self.cont_panels = cont_panels
        self.doublets = doublets
        self.linear_panels = linear_panels
        self.time = 0
        self.all = list()
        if self.vortices is not None:
            self.all += self.vortices
        if self.sources is not None:
            self.all += self.sources
        if self.freestreams is not None:
            self.all += self.freestreams
        if self.doublets is not None:
            self.all += self.doublets

    def reset(self):
        for i in self.all:
            if hasattr(i,'location'):
                i.location = i.path[0]
                i.path = i.path[0:1]
        if self.tracers is not None:
            for i in self.tracers:
                i.location = i.path[0]
                i.path = i.path[0:1]


    def total_potential(self, x, y):
        @np.vectorize
        def get_potential(x,y):
            result = complex()
            for element in self.all:
                result = result + element.potential(complex(x,y))
            return result
        return get_potential(x,y)

    def total_potential_gradient(self, x, y):
        @np.vectorize
        def get_potential_grad(x,y):
            result = complex()
            for element in self.all:
                result = result + element.potential_grad(complex(x,y))
            return result
        return get_potential_grad(x,y)

    def get_velocity(self, x,y):
        @np.vectorize
        def get_vel(x,y):
            location = complex(x,y)
            velocity = complex(self.total_potential_gradient(x,y).real,(-1*(self.total_potential_gradient(x,y).imag)))
            if self.cont_panels is not None:
                for i in self.cont_panels:
                    velocity += i.get_velocity(location)
            if self.linear_panels is not None:
                for i in self.linear_panels:
                    velocity += i.get_velocity(location)
            return velocity

        return get_vel(x,y)

    def get_element_velocity(self, element):
        '''
        returns complex velocity of an element due to all the other elements
        '''
        temp_set = set(self.all)
        temp_set.remove(element)
        velocity = complex()
        for i in temp_set:
            velocity = velocity + i.get_velocity(element.location)
        if self.cont_panels is not None:
            for i in self.cont_panels:
                velocity += i.get_velocity(element.location)
        if self.linear_panels is not None:
            for i in self.linear_panels:
                velocity += i.get_velocity(element.location)
        return velocity

    def get_element_velocity_krasny(self, element, delta):
        '''
        returns complex velocity of an element due to all the other elements
        '''
        temp_set = set(self.all)
        temp_set.remove(element)
        velocity = complex()
        for i in temp_set:
            velocity = velocity + i.get_krasny_velocity(element.location, delta)
        if self.cont_panels is not None:
            for i in self.cont_panels:
                velocity += i.get_velocity(element.location)

        return velocity

    def update_euler(self, time_step):

        #get steps for each element
        self.time = self.time + time_step
        if self.vortices is not None:
            for vortex in self.vortices:
                if vortex.fixed is not True:
                    vortex.step = self.get_element_velocity(vortex)*time_step

        if self.tracers is not None:
            for tracer in self.tracers:
                tracer.step = self.get_velocity(tracer.location.real, tracer.location.imag)*time_step

        if self.sources is not None:
            for source in self.sources:
                if source.fixed is not True:
                    source.step = self.get_element_velocity(source)*time_step

        #update the positions of each element

        if self.vortices is not None:
            for vortex in self.vortices:
                if vortex.fixed is not True:
                    vortex.location = vortex.location + vortex.step
                    vortex.path.append(complex(vortex.location))


        if self.sources is not None:
            for source in self.sources:
                if source.fixed is not True:
                    source.location = source.location + source.step
                    source.path.append(complex(source.location))


        if self.tracers is not None:
            for tracer in self.tracers:
                tracer.location = tracer.location + tracer.step
                tracer.path.append(complex(tracer.location))

    def update_RK2(self, time_step):
        self.time = self.time + time_step
        time_step = float(time_step)

        #get steps for each element
        time_step = time_step/2

        if self.vortices is not None:
            for vortex in self.vortices:
                if vortex.fixed is not True:
                    vortex.step = self.get_element_velocity(vortex)*time_step

        if self.tracers is not None:
            for tracer in self.tracers:
                tracer.step = self.get_velocity(tracer.location.real, tracer.location.imag)*time_step

        if self.sources is not None:
            for source in self.sources:
                if source.fixed is not True:
                    source.step = self.get_element_velocity(source)*time_step

        #update the positions of each element

        if self.vortices is not None:
            for vortex in self.vortices:
                if vortex.fixed is not True:
                    vortex.location = vortex.location + vortex.step
                    vortex.path.append(complex(vortex.location))

        if self.sources is not None:
            for source in self.sources:
                if source.fixed is not True:
                    source.location = source.location + source.step
                    source.path.append(complex(source.location))

        if self.tracers is not None:
            for tracer in self.tracers:
                tracer.location = tracer.location + tracer.step
                tracer.path.append(complex(tracer.location))

        if self.cont_panels is not None:
            for con in self.cont_panels:
                con.solve(0, self)
        if self.linear_panels is not None:
            for lin in self.linear_panels:
                lin.solve(0 ,self)

        #get steps for each element
        time_step = time_step*2

        if self.vortices is not None:
            for vortex in self.vortices:
                if vortex.fixed is not True:
                    vortex.step = self.get_element_velocity(vortex)*time_step - vortex.step

        if self.tracers is not None:
            for tracer in self.tracers:
                tracer.step = self.get_velocity(tracer.location.real, tracer.location.imag)*time_step - tracer.step

        if self.sources is not None:
            for source in self.sources:
                if source.fixed is not True:
                    source.step = self.get_element_velocity(source)*time_step - source.step

        #update the positions of each element

        if self.vortices is not None:
            for vortex in self.vortices:
                if vortex.fixed is not True:
                    vortex.location = vortex.location + vortex.step
                    vortex.path.append(complex(vortex.location))

        if self.sources is not None:
            for source in self.sources:
                if source.fixed is not True:
                    source.location = source.location + source.step
                    source.path.append(complex(source.location))

        if self.tracers is not None:
            for tracer in self.tracers:
                tracer.location = tracer.location + tracer.step
                tracer.path.append(complex(tracer.location))

    def update_RK2_krasny(self, time_step,delta):
        self.time = self.time + time_step
        time_step = float(time_step)

        #get steps for each element
        time_step = time_step/2

        if self.vortices is not None:
            for vortex in self.vortices:
                if vortex.fixed is not True:
                    vortex.step = self.get_element_velocity_krasny(vortex, delta)*time_step

        if self.tracers is not None:
            for tracer in self.tracers:
                tracer.step = self.get_velocity(tracer.location.real, tracer.location.imag)*time_step

        if self.sources is not None:
            for source in self.sources:
                if source.fixed is not True:
                    source.step = self.get_element_velocity(source)*time_step

        #update the positions of each element

        if self.vortices is not None:
            for vortex in self.vortices:
                if vortex.fixed is not True:
                    vortex.location = vortex.location + vortex.step
                    vortex.path.append(complex(vortex.location))

        if self.sources is not None:
            for source in self.sources:
                if source.fixed is not True:
                    source.location = source.location + source.step
                    source.path.append(complex(source.location))

        if self.tracers is not None:
            for tracer in self.tracers:
                tracer.location = tracer.location + tracer.step
                tracer.path.append(complex(tracer.location))

        #get steps for each element
        time_step = time_step*2

        if self.vortices is not None:
            for vortex in self.vortices:
                if vortex.fixed is not True:
                    vortex.step = self.get_element_velocity_krasny(vortex, delta)*time_step - vortex.step

        if self.tracers is not None:
            for tracer in self.tracers:
                tracer.step = self.get_velocity(tracer.location.real, tracer.location.imag)*time_step - tracer.step

        if self.sources is not None:
            for source in self.sources:
                if source.fixed is not True:
                    source.step = self.get_element_velocity(source)*time_step - source.step

        #update the positions of each element

        if self.vortices is not None:
            for vortex in self.vortices:
                if vortex.fixed is not True:
                    vortex.location = vortex.location + vortex.step
                    vortex.path.append(complex(vortex.location))

        if self.sources is not None:
            for source in self.sources:
                if source.fixed is not True:
                    source.location = source.location + source.step
                    source.path.append(complex(source.location))

        if self.tracers is not None:
            for tracer in self.tracers:
                tracer.location = tracer.location + tracer.step
                tracer.path.append(complex(tracer.location))