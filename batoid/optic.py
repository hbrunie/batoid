import batoid
import numpy as np

from .constants import globalCoordSys, vacuum


class Optic:
    """This is the most general category of batoid optical system.  It can include
    a single reflective or refractive surface, a lens consisting of two surfaces, or
    an entire telescope including multiple mirrors and/or surfaces.

    Parameters
    ----------
        name : str or None
            An optional name for this optic

        inMedium : batoid.Medium
            Medium in which approaching rays reside

        outMedium : batoid.Medium
            Medium in which rays will leave this optic

        coordSys : batoid.CoordSys
            Coordinate system indicating the position and orientation of this optic's vertex
            with respect to it's parent's coordinate system.  Optics can be nested, i.e., a camera
            Optic may contain several lens Optics, and may itself be part of a larger telescope
            Optic.

        skip : bool
            Whether or not to skip this optic when tracing.

        **kwargs : other
            Other attributes to add as object attributes.
    """
    def __init__(self, name=None, coordSys=globalCoordSys, inMedium=vacuum,
                 outMedium=vacuum, skip=False, **kwargs):
        self.name = name
        self.coordSys = coordSys
        self.inMedium = inMedium
        self.outMedium = outMedium
        self.skip = False
        kwargs.pop('_itemDict', None)
        self.__dict__.update(**kwargs)

    def _repr_helper(self):
        out = ""
        if self.name is not None:
            out += ", name={!r}".format(self.name)
        out += ", coordSys={!r}".format(self.coordSys)
        if self.inMedium != vacuum:
            out += ", inMedium={!r}".format(self.inMedium)
        if self.outMedium != vacuum:
            out += ", outMedium={!r}".format(self.outMedium)
        return out


class Interface(Optic):
    """The most basic category of Optic representing a single surface.  Almost always one of the
    concrete subclasses should be instantiated, depending on whether rays should reflect, refract,
    or simply pass through this surface.

    Parameters
    ----------
        surface : batoid.Surface
            The surface instance for this Interface.

        obscuration : batoid.Obscuration or None
            Batoid.Obscuration instance indicating which x,y coordinates are obscured/unobscured
            for rays intersecting this optic.

        **kwargs :
            Other parameters to forward to Optic.__init__.
    """
    def __init__(self, surface, obscuration=None, **kwargs):
        Optic.__init__(self, **kwargs)

        self.surface = surface
        self.obscuration = obscuration

        # Stealing inRadius and outRadius from self.obscuration.  These are required for the draw
        # methods.
        self.inRadius = 0.0
        self.outRadius = None
        if self.obscuration is not None:
            if isinstance(self.obscuration, batoid.ObscNegation):
                if isinstance(self.obscuration.original, batoid.ObscCircle):
                    self.outRadius = self.obscuration.original.radius
                elif isinstance(self.obscuration.original, batoid.ObscAnnulus):
                    self.outRadius = self.obscuration.original.outer
                    self.inRadius = self.obscuration.original.inner
            elif isinstance(self.obscuration, batoid.ObscCircle):
                self.outRadius = self.obscuration.radius
            elif isinstance(self.obscuration, batoid.ObscAnnulus):
                self.outRadius = self.obscuration.outer
                self.inRadius = self.obscuration.inner

    def __hash__(self):
        return hash((self.__class__.__name__, self.surface, self.obscuration, self.name,
                     self.inMedium, self.outMedium, self.coordSys))

    def draw3d(self, ax, **kwargs):
        """ Draw this interface on a mplot3d axis.

        Parameters
        ----------

            ax : mplot3d.Axis
                Axis on which to draw this optic.
        """
        if self.outRadius is None:
            return
        # Going to draw 4 objects here: inner circle, outer circle, sag along x=0, sag along y=0
        # inner circle
        if self.inRadius != 0.0:
            th = np.linspace(0, 2*np.pi, 100)
            cth, sth = np.cos(th), np.sin(th)
            x = self.inRadius * cth
            y = self.inRadius * sth
            z = self.surface.sag(x, y)
            transform = batoid.CoordTransform(self.coordSys, globalCoordSys)
            x, y, z = transform.applyForward(x, y, z)
            ax.plot(x, y, z, **kwargs)

        #outer circle
        th = np.linspace(0, 2*np.pi, 100)
        cth, sth = np.cos(th), np.sin(th)
        x = self.outRadius * cth
        y = self.outRadius * sth
        z = self.surface.sag(x, y)
        transform = batoid.CoordTransform(self.coordSys, globalCoordSys)
        x, y, z = transform.applyForward(x, y, z)
        ax.plot(x, y, z, **kwargs)

        #next, a line at X=0
        y = np.linspace(-self.outRadius, -self.inRadius)
        x = np.zeros_like(y)
        z = self.surface.sag(x, y)
        transform = batoid.CoordTransform(self.coordSys, globalCoordSys)
        x, y, z = transform.applyForward(x, y, z)
        ax.plot(x, y, z, **kwargs)
        y = np.linspace(self.inRadius, self.outRadius)
        x = np.zeros_like(y)
        z = self.surface.sag(x, y)
        transform = batoid.CoordTransform(self.coordSys, globalCoordSys)
        x, y, z = transform.applyForward(x, y, z)
        ax.plot(x, y, z, **kwargs)

        #next, a line at Y=0
        x = np.linspace(-self.outRadius, -self.inRadius)
        y = np.zeros_like(x)
        z = self.surface.sag(x, y)
        transform = batoid.CoordTransform(self.coordSys, globalCoordSys)
        x, y, z = transform.applyForward(x, y, z)
        ax.plot(x, y, z, **kwargs)
        x = np.linspace(self.inRadius, self.outRadius)
        y = np.zeros_like(x)
        z = self.surface.sag(x, y)
        transform = batoid.CoordTransform(self.coordSys, globalCoordSys)
        x, y, z = transform.applyForward(x, y, z)
        ax.plot(x, y, z, **kwargs)

    def getXZSlice(self, nslice=0):
        """Calculate global coordinates for an (x,z) slice through this interface.

        The calculation is split into two half slices: xlocal <= 0 and xlocal >= 0.
        When the inner radius is zero, these half slices are merged into one.
        Otherwise, the two half slices are returned separately.

        If the local coordinate system involves any rotation the resulting
        slice may not be calculated correctly since we are really slicing in
        (xlocal, zlocal) then transforming these to (xglobal, zglobal).

        Parameters
        ----------
        nslice : int
            Use the specified number of points on each half slice. When zero,
            the value will be calculated automatically (and will be 2 for
            planar surfaces).

        Returns
        -------
        tuple
            Tuple (xz1, xz2) of 1D arrays where xz1=[x1, z1] is the xlocal <= 0
            half slice and xz2=[x2, z2] is the xlocal >= 0 half slice.
        """
        slice = []
        if self.outRadius is None:
            return slice
        if nslice <= 0:
            if isinstance(self.surface, batoid.surface.Plane):
                nslice = 2
            else:
                nslice = 50
        # Calculate (x,z) slice in local coordinates for x <= 0.
        x = np.linspace(-self.outRadius, -self.inRadius, nslice)
        y = np.zeros_like(x)
        z = self.surface.sag(x, y)
        # Transform slice to global coordinates.
        transform = batoid.CoordTransform(self.coordSys, batoid.globalCoordSys)
        xneg, yneg, zneg = transform.applyForward(x, y, z)
        if np.any(yneg != 0):
            print('WARNING: getXZSlice used for rotated surface "{0}".'.format(self.name))
        # Calculate (x,z) slice in local coordinates for x >= 0.
        x *= -1
        x = x[::-1]
        z[:] = self.surface.sag(x, y)
        # Transform slice to global coordinates.
        xpos, ypos, zpos = transform.applyForward(x, y, z)
        if np.any(ypos != 0):
            print('WARNING: getXZSlice used for rotated surface "{0}".'.format(self.name))
        slice.append(np.stack((xpos, zpos), axis=0))
        # Combine x <= 0 and x >= 0 half slices when inner = 0.
        if self.inRadius == 0:
            assert xneg[-1] == xpos[0] and zneg[-1] == zpos[0]
            return (
                np.stack((
                    np.hstack((xneg, xpos[1:])),
                    np.hstack((zneg, zpos[1:]))
                ), axis=0),
            )
        else:
            return (np.stack((xneg, zneg), axis=0), np.stack((xpos, zpos), axis=0))

    def draw2d(self, ax, **kwargs):
        """ Draw this interface on a 2d matplotlib axis.
        May not work if elements are non-circular or not axis-aligned.
        """
        slice = self.getXZSlice()
        for x, z in slice:
            ax.plot(x, z, **kwargs)

    def trace(self, r, inCoordSys=globalCoordSys, outCoordSys=None):
        """ Trace a ray through this optical element.

        Parameters
        ----------

        r : batoid.Ray or batoid.RayVector
            input ray to trace

        inCoordSys : batoid.CoordSys
            Coordinate system of incoming ray(s).  Default: the global coordinate system.

        outCoordSys : batoid.CoordSys
            Coordinate system into which to project the output ray(s).  Default: None,
            which means use the coordinate system of the optic.

        Returns
        -------
            Ray or RayVector, output CoordSys.

        """
        if self.skip:
            return r, inCoordSys
        transform = batoid.CoordTransform(inCoordSys, self.coordSys)
        r = transform.applyForward(r)

        # refract, reflect, pass-through - depending on subclass
        r = self.interact(r)

        if self.obscuration is not None:
            r = self.obscuration.obscure(r)

        if outCoordSys is None:
            return r, self.coordSys
        else:
            transform = batoid.CoordTransform(self.coordSys, outCoordSys)
            return transform.applyForward(r), outCoordSys

    def traceFull(self, r, inCoordSys=globalCoordSys, outCoordSys=None):
        if self.skip:
            return []
        result = [{'name':self.name, 'in':r, 'inCoordSys':inCoordSys}]
        r, outCoordSys = self.trace(r, inCoordSys=inCoordSys, outCoordSys=outCoordSys)
        result[0]['out'] = r
        result[0]['outCoordSys'] = outCoordSys
        return result

    def traceInPlace(self, r, inCoordSys=globalCoordSys, outCoordSys=None):
        if self.skip:
            return r, inCoordSys
        transform = batoid.CoordTransform(inCoordSys, self.coordSys)
        transform.applyForwardInPlace(r)

        # refract, reflect, pass-through - depending on subclass
        self.interactInPlace(r)

        if self.obscuration is not None:
            self.obscuration.obscureInPlace(r)

        if outCoordSys is None:
            return r, self.coordSys
        else:
            transform = batoid.CoordTransform(self.coordSys, outCoordSys)
            transform.applyForwardInPlace(r)
            return r, outCoordSys

    def traceReverse(self, r, inCoordSys=globalCoordSys, outCoordSys=None):
        """Trace through optic(s) in reverse.  Note, you may need to reverse the direction
        of rays for this to work.
        """
        if self.skip:
            return r, inCoordSys
        transform = batoid.CoordTransform(inCoordSys, self.coordSys)
        r = transform.applyForward(r)

        r = self.interactReverse(r)

        if self.obscuration is not None:
            r = self.obscuration.obscure(r)

        if outCoordSys is None:
            return r, self.coordSys
        else:
            transform = batoid.CoordTransform(self.coordSys, outCoordSys)
            return transform.applyForward(r), outCoordSys

    def traceSplit(self, r, inCoordSys=globalCoordSys, forwardCoordSys=None, reverseCoordSys=None,
                   minFlux=1e-3, verbose=False):
        """Assume Rays are coming in from the forward direction.
        returns forwardRays, forwardCoordSys, reverseRays, reverseCoordSys
        """
        if verbose:
            strtemplate = "traceSplit        {:15s} flux = {:18.8f}   nphot = {:10d}"
            print(strtemplate.format(self.name, np.sum(r.flux), len(r)))
        if self.skip:
            return r, None, inCoordSys, None
        transform = batoid.CoordTransform(inCoordSys, self.coordSys)
        r = transform.applyForward(r)

        rForward, rReverse = self.rSplit(r)

        # For now, apply obscuration equally forwards and backwards
        if self.obscuration is not None:
            rForward = self.obscuration.obscure(rForward)
            rReverse = self.obscuration.obscure(rReverse)

        if forwardCoordSys is None:
            forwardCoordSys = self.coordSys
        else:
            transform = batoid.CoordTransform(self.coordSys, forwardCoordSys)
            rForward = transform.applyForward(rForward)

        if reverseCoordSys is None:
            reverseCoordSys = self.coordSys
        else:
            transform = batoid.CoordTransform(self.coordSys, reverseCoordSys)
            rReverse = transform.applyForward(rReverse)

        return rForward, rReverse, forwardCoordSys, reverseCoordSys

    def traceSplitReverse(self, r, inCoordSys=globalCoordSys, forwardCoordSys=None,
                          reverseCoordSys=None, minFlux=1e-3, verbose=False):
        """Assume Rays are coming in from the reverse direction.
        returns forwardRays, forwardCoordSys, reverseRays, reverseCoordSys
        """
        if verbose:
            strtemplate = "traceSplitReverse {:15s} flux = {:18.8f}   nphot = {:10d}"
            print(strtemplate.format(self.name, np.sum(r.flux), len(r)))
        if self.skip:
            return r, None, inCoordSys, None
        transform = batoid.CoordTransform(inCoordSys, self.coordSys)
        r = transform.applyForward(r)

        rForward, rReverse = self.rSplitReverse(r)

        # For now, apply obscuration equally forwards and backwards
        if self.obscuration is not None:
            rForward = self.obscuration.obscure(rForward)
            rReverse = self.obscuration.obscure(rReverse)

        if forwardCoordSys is None:
            forwardCoordSys = self.coordSys
        else:
            transform = batoid.CoordTransform(self.coordSys, forwardCoordSys)
            rForward = transform.applyForward(rForward)

        if reverseCoordSys is None:
            reverseCoordSys = self.coordSys
        else:
            transform = batoid.CoordTransform(self.coordSys, reverseCoordSys)
            rReverse = transform.applyForward(rReverse)

        return rForward, rReverse, forwardCoordSys, reverseCoordSys

    def __eq__(self, other):
        if not self.__class__ == other.__class__:
            return False
        return (self.surface == other.surface and
                self.obscuration == other.obscuration and
                self.name == other.name and
                self.inMedium == other.inMedium and
                self.outMedium == other.outMedium and
                self.coordSys == other.coordSys)

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        out = "{!s}({!r}".format(self.__class__.__name__, self.surface)
        if self.obscuration is not None:
            out += ", obscuration={!r}".format(self.obscuration)
        out += Optic._repr_helper(self)
        out +=")"
        return out

    def withGlobalShift(self, shift):
        ret = self.__class__.__new__(self.__class__)
        newDict = dict(self.__dict__)
        newDict['coordSys'] = self.coordSys.shiftGlobal(shift)
        del newDict['surface']
        ret.__init__(
            self.surface,
            **newDict
        )
        return ret

    def withLocalRotation(self, rot, rotOrigin=None, coordSys=None):
        if rotOrigin is None and coordSys is None:
            coordSys = self.coordSys
            rotOrigin = [0,0,0]
        ret = self.__class__.__new__(self.__class__)
        newDict = dict(self.__dict__)
        newDict['coordSys'] = self.coordSys.rotateLocal(rot, rotOrigin, coordSys)
        del newDict['surface']
        ret.__init__(
            self.surface,
            **newDict
        )
        return ret


class RefractiveInterface(Interface):
    """Specialization for refractive interfaces.
    """
    def __init__(self, *args, **kwargs):
        Interface.__init__(self, *args, **kwargs)
        # self.forwardCoating = batoid.SimpleCoating(reflectivity=0.0, transmissivity=1.0)
        # self.reverseCoating = batoid.SimpleCoating(reflectivity=0.0, transmissivity=1.0)
        self.forwardCoating = batoid.SimpleCoating(reflectivity=0.02, transmissivity=0.98)
        self.reverseCoating = batoid.SimpleCoating(reflectivity=0.02, transmissivity=0.98)

    def interact(self, r):
        return self.surface.refract(r, self.inMedium, self.outMedium)

    def interactReverse(self, r):
        return self.surface.refract(r, self.outMedium, self.inMedium)

    def interactInPlace(self, r):
        self.surface.refractInPlace(r, self.inMedium, self.outMedium)

    def rSplit(self, r):
        reflectedR, refractedR = self.surface.rSplit(r, self.inMedium, self.outMedium,
                                                     self.forwardCoating)
        return refractedR, reflectedR

    def rSplitReverse(self, r):
        reflectedR, refractedR = self.surface.rSplit(r, self.outMedium, self.inMedium,
                                                     self.reverseCoating)
        # rays coming into a refractive interface from reverse direction,
        # means that the refracted rays are going in the reverse direction,
        # and the reflected rays are going in the forward direction.
        # so return reflected (forward) first.
        return reflectedR, refractedR


class Mirror(Interface):
    """Specialization for reflective interfaces.
    """
    def __init__(self, *args, **kwargs):
        Interface.__init__(self, *args, **kwargs)
        self.forwardCoating = batoid.SimpleCoating(reflectivity=1.0, transmissivity=0.0)
        self.reverseCoating = batoid.SimpleCoating(reflectivity=1.0, transmissivity=0.0)

    def interact(self, r):
        return self.surface.reflect(r)

    def interactReverse(self, r):
        return self.surface.reflect(r)

    def interactInPlace(self, r):
        self.surface.reflectInPlace(r)

    def rSplit(self, r):
        reflectedR, refractedR = self.surface.rSplit(r, self.inMedium, self.outMedium,
                                                     self.forwardCoating)
        return reflectedR, refractedR

    def rSplitReverse(self, r):
        reflectedR, refractedR = self.surface.rSplit(r, self.outMedium, self.inMedium,
                                                     self.reverseCoating)
        return refractedR, reflectedR


class Detector(Interface):
    """Specialization for detector interfaces.
    """
    def __init__(self, *args, **kwargs):
        Interface.__init__(self, *args, **kwargs)
        self.forwardCoating = batoid.SimpleCoating(reflectivity=0.02, transmissivity=0.98)
        self.reverseCoating = None

    def interact(self, r):
        return self.surface.intersect(r)

    def interactReverse(self, r):
        return self.surface.intersect(r)

    def interactInPlace(self, r):
        self.surface.intersectInPlace(r)

    def rSplit(self, r):
        reflectedR, refractedR = self.surface.rSplit(r, self.inMedium, self.outMedium,
                                                     self.forwardCoating)
        return refractedR, reflectedR

    def rSplitReverse(self, r):
        reflectedR, refractedR = self.surface.rSplit(r, self.outMedium, self.inMedium,
                                                     self.reverseCoating)
        return reflectedR, refractedR


class Baffle(Interface):
    """Specialization for baffle interfaces.  Rays will be reported here, but pass through in
    straight lines.
    """
    def __init__(self, *args, **kwargs):
        Interface.__init__(self, *args, **kwargs)
        self.forwardCoating = batoid.SimpleCoating(reflectivity=0.0, transmissivity=1.0)
        self.reverseCoating = batoid.SimpleCoating(reflectivity=0.0, transmissivity=1.0)

    def interact(self, r):
        return self.surface.intersect(r)

    def interactReverse(self, r):
        return self.surface.intersect(r)

    def interactInPlace(self, r):
        self.surface.intersectInPlace(r)

    def rSplit(self, r):
        reflectedR, refractedR = self.surface.rSplit(r, self.inMedium, self.outMedium,
                                                     self.forwardCoating)
        return refractedR, reflectedR

    def rSplitReverse(self, r):
        reflectedR, refractedR = self.surface.rSplit(r, self.outMedium, self.inMedium,
                                                     self.reverseCoating)
        return reflectedR, refractedR


class CompoundOptic(Optic):
    """A Optic containing two or more Optics as subitems.
    """
    def __init__(self, items, **kwargs):
        Optic.__init__(self, **kwargs)
        self.items = tuple(items)

    @property
    def itemDict(self):
        """A dictionary providing convenient access to the entire hierarchy of this CompoundOptic's
        constituent components.  The key for the first level is just the name of the CompoundOptic,
        e.g., `optic.itemDict['SubaruHSC']`.  The next level is accessed by appending a `.`, e.g.,
        `optic.itemDict['SubaruHSC.HSC']` and so on:
        `optic.itemDict['SubaruHSC.HSC.ADC']`
        `optic.itemDict['SubaruHSC.HSC.ADC.ADC1']`
        `optic.itemDict['SubaruHSC.HSC.ADC.ADC1.ADC1_entrance']`
        """
        if not hasattr(self, '_itemDict'):
            self._itemDict = {}
            self._itemDict[self.name] = self
            for item in self.items:
                self._itemDict[self.name+'.'+item.name] = item
                if hasattr(item, 'itemDict'):
                    for k, v in item.itemDict.items():
                        self._itemDict[self.name+'.'+k] = v
        return self._itemDict

    def trace(self, r, inCoordSys=globalCoordSys, outCoordSys=None):
        """ Recursively trace through this Optic by successively tracing through all subitems.
        """
        if self.skip:
            return r, inCoordSys # should maybe make a copy of r here?
        coordSys = inCoordSys
        for item in self.items[:-1]:
            if not item.skip:
                r, coordSys = item.trace(r, inCoordSys=coordSys)
        return self.items[-1].trace(r, inCoordSys=coordSys, outCoordSys=outCoordSys)

    def traceInPlace(self, r, inCoordSys= globalCoordSys, outCoordSys=None):
        if self.skip:
            return r, inCoordSys
        coordSys = inCoordSys
        for item in self.items[:-1]:
            r, coordSys = item.traceInPlace(r, inCoordSys=coordSys)
        return self.items[-1].traceInPlace(r, inCoordSys=coordSys, outCoordSys=outCoordSys)

    def traceFull(self, r, inCoordSys=globalCoordSys, outCoordSys=None):
        """ Recursively trace through this Optic by successively tracing through all subitems.

        The return value will contain the incoming and outgoing rays for each Interface.
        """
        if self.skip:
            return []
        result = []
        r_in = r
        coordSys = inCoordSys
        for item in self.items[:-1]:
            result.extend(item.traceFull(r_in, inCoordSys=coordSys))
            r_in = result[-1]['out']
            coordSys = result[-1]['outCoordSys']
        result.extend(self.items[-1].traceFull(r_in, inCoordSys=coordSys, outCoordSys=outCoordSys))
        return result

    def traceReverse(self, r, inCoordSys=globalCoordSys, outCoordSys=None):
        """Trace through optic(s) in reverse.  Note, you may need to reverse the direction
        of rays for this to work.
        """
        if self.skip:
            return r, inCoordSys
        coordSys = inCoordSys
        for item in reversed(self.items[1:]):
            if not item.skip:
                r, coordSys = item.traceReverse(r, inCoordSys=coordSys)
        return self.items[0].traceReverse(r, inCoordSys=coordSys, outCoordSys=outCoordSys)

    def traceSplit(self, r, inCoordSys=globalCoordSys, forwardCoordSys=None, reverseCoordSys=None,
                   minFlux=1e-3, verbose=False):
        if verbose:
            strtemplate = "traceSplit        {:15s} flux = {:18.8f}   nphot = {:10d}"
            print(strtemplate.format(self.name, np.sum(r.flux), len(r)))
        if self.skip:
            return r, None, inCoordSys, None

        if forwardCoordSys is None:
            forwardCoordSys = self.items[-1].coordSys
        if reverseCoordSys is None:
            reverseCoordSys = self.items[0].coordSys

        workQueue = [(r, inCoordSys, "forward", 0)]

        outRForward = []
        outRReverse = []

        while workQueue:
            rays, inCoordSys, direction, itemIndex = workQueue.pop()
            item = self.items[itemIndex]
            if direction == "forward":
                rForward, rReverse, tmpForwardCoordSys, tmpReverseCoordSys = \
                    item.traceSplit(rays, inCoordSys, minFlux=minFlux, verbose=verbose)
            elif direction == "reverse":
                rForward, rReverse, tmpForwardCoordSys, tmpReverseCoordSys = \
                    item.traceSplitReverse(rays, inCoordSys, minFlux=minFlux, verbose=verbose)
            else:
                raise RuntimeError("Shouldn't get here!")

            rForward.trimVignettedInPlace(minFlux)
            rReverse.trimVignettedInPlace(minFlux)

            if itemIndex == 0:
                if len(rReverse) > 0:
                    if tmpReverseCoordSys != reverseCoordSys:
                        transform = batoid.CoordTransform(tmpReverseCoordSys, reverseCoordSys)
                        transform.applyForwardInPlace(rReverse)
                    outRReverse.append(rReverse)
            else:
                if len(rReverse) > 0:
                    workQueue.append((rReverse, tmpReverseCoordSys, "reverse", itemIndex-1))

            if itemIndex == len(self.items)-1:
                if len(rForward) > 0:
                    if tmpForwardCoordSys != forwardCoordSys:
                        transform = batoid.CoordTransform(tmpForwardCoordSys, forwardCoordSys)
                        transform.applyForwardInPlace(rForward)
                    outRForward.append(rForward)
            else:
                if len(rForward) > 1:
                    workQueue.append((rForward, tmpForwardCoordSys, "forward", itemIndex+1))

        rForward = batoid.concatenateRayVectors(outRForward)
        rReverse = batoid.concatenateRayVectors(outRReverse)
        return rForward, rReverse, forwardCoordSys, reverseCoordSys

    def traceSplitReverse(self, r, inCoordSys=globalCoordSys, forwardCoordSys=None,
                          reverseCoordSys=None, minFlux=1e-3, verbose=False):
        if verbose:
            strtemplate = "traceSplitReverse {:15s} flux = {:18.8f}   nphot = {:10d}"
            print(strtemplate.format(self.name, np.sum(r.flux), len(r)))
        if self.skip:
            return r, None, inCoordSys, None

        if forwardCoordSys is None:
            forwardCoordSys = self.items[-1].coordSys
        if reverseCoordSys is None:
            reverseCoordSys = self.items[0].coordSys

        workQueue = [(r, inCoordSys, "reverse", len(self.items)-1)]

        outRForward = []
        outRReverse = []

        while workQueue:
            rays, inCoordSys, direction, itemIndex = workQueue.pop()
            item = self.items[itemIndex]
            if direction == "forward":
                rForward, rReverse, tmpForwardCoordSys, tmpReverseCoordSys = \
                    item.traceSplit(rays, inCoordSys, minFlux=minFlux, verbose=verbose)
            elif direction == "reverse":
                rForward, rReverse, tmpForwardCoordSys, tmpReverseCoordSys = \
                    item.traceSplitReverse(rays, inCoordSys, minFlux=minFlux, verbose=verbose)
            else:
                raise RuntimeError("Shouldn't get here!")

            rForward.trimVignettedInPlace(minFlux)
            rReverse.trimVignettedInPlace(minFlux)

            if itemIndex == 0:
                if len(rReverse) > 0:
                    if tmpReverseCoordSys != reverseCoordSys:
                        transform = batoid.CoordTransform(tmpReverseCoordSys, reverseCoordSys)
                        transform.applyForwardInPlace(rReverse)
                    outRReverse.append(rReverse)
            else:
                if len(rReverse) > 0:
                    workQueue.append((rReverse, tmpReverseCoordSys, "reverse", itemIndex-1))

            if itemIndex == len(self.items)-1:
                if len(rForward) > 0:
                    if tmpForwardCoordSys != forwardCoordSys:
                        transform = batoid.CoordTransform(tmpForwardCoordSys, forwardCoordSys)
                        transform.applyForwardInPlace(rForward)
                    outRForward.append(rForward)
            else:
                if len(rForward) > 1:
                    workQueue.append((rForward, tmpForwardCoordSys, "forward", itemIndex+1))

        rForward = batoid.concatenateRayVectors(outRForward)
        rReverse = batoid.concatenateRayVectors(outRReverse)
        return rForward, rReverse, forwardCoordSys, reverseCoordSys

    def draw3d(self, ax, **kwargs):
        """ Recursively draw this Optic by successively drawing all subitems.
        """
        for item in self.items:
            item.draw3d(ax, **kwargs)

    def draw2d(self, ax, **kwargs):
        """Draw a 2D slice of this compound optic in the (x,z) plane.

        Calls draw2d recursively on each of our items, with the actual
        drawing taking place in Interface and (optionally) Lens instances.

        The kwargs are passed to the drawing commands, except for the
        optional keyword 'only' which restricts drawing to only instances
        that are subclasses of a specified type or types.
        """
        only = kwargs.pop('only', None)
        for item in self.items:
            item_class = item.__class__
            if issubclass(item_class, batoid.optic.CompoundOptic):
                item.draw2d(ax, only=only, **kwargs)
            elif only is None or issubclass(item_class, only):
                item.draw2d(ax, **kwargs)

    def __eq__(self, other):
        if not self.__class__ == other.__class__:
            return False
        return (self.items == other.items and
                self.name == other.name and
                self.inMedium == other.inMedium and
                self.outMedium == other.outMedium and
                self.coordSys == other.coordSys)

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        out = "{!s}([".format(self.__class__.__name__)
        for item in self.items[:-1]:
            out += "{!r}, ".format(item)
        out += "{!r}]".format(self.items[-1])
        out += Optic._repr_helper(self)
        out += ")"
        return out

    def __hash__(self):
        return hash((self.__class__.__name__, self.items,
                     self.name, self.inMedium, self.outMedium, self.coordSys))

    def withGlobalShift(self, shift):
        """Shift the origin of this optic by `shift`.
        """
        newItems = [item.withGlobalShift(shift) for item in self.items]
        ret = self.__class__.__new__(self.__class__)

        newDict = dict(self.__dict__)
        newDict['coordSys'] = self.coordSys.shiftGlobal(shift)
        del newDict['items']
        ret.__init__(
            newItems,
            **newDict
        )
        return ret

    def withGloballyShiftedOptic(self, name, shift):
        """Shift the origin of a subitem given by name (see itemDict docstring for the name format)
        by `shift`.
        """
        # If name is one of items.names, the we use withGlobalShift, and we're done.
        # If not, then we need to recurse down to whichever item contains name.
        # First verify that name is in self.itemDict
        if name not in self.itemDict:
            raise ValueError("Optic {} not found".format(name))
        if name == self.name:
            return self.withGlobalShift(shift)
        # Clip off leading token
        assert name[:len(self.name)+1] == \
            self.name+".", name[:len(self.name)+1]+" != "+self.name+"."
        name = name[len(self.name)+1:]
        newItems = []
        newDict = dict(self.__dict__)
        del newDict['items']
        for i, item in enumerate(self.items):
            if name.startswith(item.name):
                if name == item.name:
                    newItems.append(item.withGlobalShift(shift))
                else:
                    newItems.append(item.withGloballyShiftedOptic(name, shift))
                newItems.extend(self.items[i+1:])
                return self.__class__(
                    newItems,
                    **newDict
                )
            newItems.append(item)
        raise RuntimeError("Error in withGloballyShiftedOptic!, Shouldn't get here!")

    def withLocalRotation(self, rot, rotOrigin=None, coordSys=None):
        """Rotate optic by `rot`.
        """
        if rotOrigin is None and coordSys is None:
            coordSys = self.coordSys
            rotOrigin = [0,0,0]
        newItems = [item.withLocalRotation(rot, rotOrigin, coordSys) for item in self.items]
        ret = self.__class__.__new__(self.__class__)
        newDict = dict(self.__dict__)
        newDict['coordSys'] = self.coordSys.rotateLocal(rot, rotOrigin, coordSys)
        del newDict['items']
        ret.__init__(
            newItems,
            **newDict
        )
        return ret

    def withLocallyRotatedOptic(self, name, rot, rotOrigin=None, coordSys=None):
        """Rotate the subitem by `rot`.
        """
        # If name is one of items.names, the we use withLocalRotation, and we're done.
        # If not, then we need to recurse down to whichever item contains name.
        # First verify that name is in self.itemDict
        if name not in self.itemDict:
            raise ValueError("Optic {} not found".format(name))
        if name == self.name:
            return self.withLocalRotation(rot, rotOrigin, coordSys)
        if rotOrigin is None and coordSys is None:
            coordSys = self.itemDict[name].coordSys
            rotOrigin = [0,0,0]
        # Clip off leading token
        assert name[:len(self.name)+1] == \
            self.name+".", name[:len(self.name)+1]+" != "+self.name+"."
        name = name[len(self.name)+1:]
        newItems = []
        newDict = dict(self.__dict__)
        del newDict['items']
        for i, item in enumerate(self.items):
            if name.startswith(item.name):
                if name == item.name:
                    newItems.append(item.withLocalRotation(rot, rotOrigin, coordSys))
                else:
                    newItems.append(item.withLocallyRotatedOptic(name, rot, rotOrigin, coordSys))
                newItems.extend(self.items[i+1:])
                return self.__class__(
                    newItems,
                    **newDict
                )
            newItems.append(item)
        raise RuntimeError("Error in withLocallyRotatedOptic!, Shouldn't get here!")


class Lens(CompoundOptic):
    def __init__(self, items, medium, **kwargs):
        Optic.__init__(self, **kwargs)
        self.items = tuple(items)
        self.medium = medium

    def __eq__(self, other):
        if not CompoundOptic.__eq__(self, other):
            return False
        return self.medium == other.medium

    def __repr__(self):
        out = ("{!s}([{!r}, {!r}], {!r}"
               .format(self.__class__.__name__, self.items[0], self.items[1], self.medium))
        out += Optic._repr_helper(self)
        out += ")"
        return out

    def __hash__(self):
        return hash((self.medium, CompoundOptic.__hash__(self)))

    def draw2d(self, ax, **kwargs):
        """Specialized draw2d for Lens instances.

        If the optional keyword 'only' equals batoid.optic.Lens,
        then fill the area between the lens refractive interfaces
        using the remaining specified kwargs (fc, ec, alpha, ...)

        Otherwise, call draw2d on each of our refractive interfaces.

        The optional labelpos and fontdict kwargs are used to
        draw a label at the specified x position (in global coords),
        using the specified font properties.
        """
        only = kwargs.pop('only', None)
        if only == batoid.optic.Lens:
            labelpos = kwargs.pop('labelpos', None)
            fontdict = kwargs.pop('fontdict', None)
            if len(self.items) != 2:
                raise RuntimeError(
                    'Cannot draw lens "{0}" with {1} surfaces.'.format(self.name, len(self.items)))
            # Calculate the global coordinates of slices through our two interfaces.
            slice1 = self.items[0].getXZSlice()
            slice2 = self.items[1].getXZSlice()
            # Fill the area between these slices.
            all_z = []
            for (x1, z1), (x2, z2) in zip(slice1, slice2):
                x = np.hstack((x1, x2[::-1], x1[:1]))
                z = np.hstack((z1, z2[::-1], z1[:1]))
                all_z.append(z)
                ax.fill(x, z, **kwargs)
            # Draw an optional label for this lens.
            if labelpos is not None:
                zlabel = np.mean(all_z)
                ax.text(
                    labelpos, zlabel, self.name, fontdict=fontdict,
                    horizontalalignment='center', verticalalignment='center')
        else:
            super(Lens, self).draw2d(ax, only=only, **kwargs)

    def withGlobalShift(self, shift):
        newItems = [item.withGlobalShift(shift) for item in self.items]
        ret = self.__class__.__new__(self.__class__)
        newDict = dict(self.__dict__)
        newDict['coordSys'] = self.coordSys.shiftGlobal(shift)
        del newDict['items']
        del newDict['medium']
        ret.__init__(
            newItems, self.medium,
            **newDict
        )
        return ret

    def withGloballyShiftedOptic(self, name, shift):
        """Shift the origin of a subitem given by name (see itemDict docstring for the name format)
        by `shift`.
        """
        # If name is one of items.names, the we use withGlobalShift, and we're done.
        # If not, then we need to recurse down to whicever item contains name.
        # First verify that name is in self.itemDict
        if name not in self.itemDict:
            raise ValueError("Optic {} not found".format(name))
        if name == self.name:
            return self.withGlobalShift(shift)
        # Clip off leading token
        assert name[:len(self.name)+1] == \
            self.name+".", name[:len(self.name)+1]+" != "+self.name+"."
        name = name[len(self.name)+1:]
        newItems = []
        newDict = dict(self.__dict__)
        del newDict['items']
        del newDict['medium']
        for i, item in enumerate(self.items):
            if name.startswith(item.name):
                if name == item.name:
                    newItems.append(item.withGlobalShift(shift))
                else:
                    newItems.append(item.withGloballyShiftedOptic(name, shift))
                newItems.extend(self.items[i+1:])
                return self.__class__(
                    newItems, self.medium,
                    **newDict
                )
            newItems.append(item)
        raise RuntimeError("Error in withGloballyShiftedOptic!, Shouldn't get here!")

    def withLocalRotation(self, rot, rotOrigin=None, coordSys=None):
        """Rotate optic by `rot`.
        """
        if rotOrigin is None and coordSys is None:
            coordSys = self.coordSys
            rotOrigin = [0,0,0]
        newItems = [item.withLocalRotation(rot, rotOrigin, coordSys) for item in self.items]
        newDict = dict(self.__dict__)
        del newDict['items']
        del newDict['medium']
        ret = self.__class__.__new__(self.__class__)
        ret.__init__(
            newItems, self.medium,
            **newDict
        )
        return ret

    def withLocallyRotatedOptic(self, name, rot, rotOrigin=None, coordSys=None):
        """Rotate the subitem by `rot`.
        """
        # If name is one of items.names, the we use withLocalRotation, and we're done.
        # If not, then we need to recurse down to whichever item contains name.
        # First verify that name is in self.itemDict
        if name not in self.itemDict:
            raise ValueError("Optic {} not found".format(name))
        if name == self.name:
            return self.withLocalRotation(rot, rotOrigin, coordSys)
        if rotOrigin is None and coordSys is None:
            coordSys = self.itemDict[name].coordSys
            rotOrigin = [0,0,0]
        # Clip off leading token
        assert name[:len(self.name)+1] == \
            self.name+".", name[:len(self.name)+1]+" != "+self.name+"."
        name = name[len(self.name)+1:]
        newItems = []
        newDict = dict(self.__dict__)
        del newDict['items']
        del newDict['medium']
        for i, item in enumerate(self.items):
            if name.startswith(item.name):
                if name == item.name:
                    newItems.append(item.withLocalRotation(rot, rotOrigin, coordSys))
                else:
                    newItems.append(item.withLocallyRotatedOptic(name, rot, rotOrigin, coordSys))
                newItems.extend(self.items[i+1:])
                return self.__class__(
                    newItems, self.medium,
                    **newDict
                )
            newItems.append(item)
        raise RuntimeError("Error in withLocallyRotatedOptic!, Shouldn't get here!")


def getGlobalRays(traceFull, start=None, end=None, globalSys=globalCoordSys):
    """Calculate an array of ray vertices in global coordinates.

    Parameters
    ----------
    traceFull : array
        Array of per-surface ray-tracing output from traceFull()
    start : str or None
        Name of the first surface to include in the output, or use the first
        surface in the model when None.
    end : str or None
        Name of the last surface to include in the output, or use the last
        surface in the model when None.
    globalSys : batoid.CoordSys
        Global coordinate system to use.
    
    Returns
    -------
    tuple
        Tuple (xyz, raylen) of arrays with shapes (nray, 3, nsurf + 1) and
        (nray,).  The xyz array contains the global coordinates of each
        ray vertex, with raylen giving the number of visible (not vignetted)
        vertices for each ray.
    """
    names = [trace['name'] for trace in traceFull]
    try:
        start = 0 if start is None else names.index(start)
    except ValueError:
        raise ValueError('No such start surface "{0}".'.format(start))
    try:
        end = len(names) if end is None else names.index(end) + 1
    except ValueError:
        raise ValueError('No such end surface "{0}".'.format(end))
    nsurf = end - start
    if nsurf <= 0:
        raise ValueError('Expected start < end.')
    nray = len(traceFull[start]['in'])
    # Allocate an array for all ray vertices in global coords.
    xyz = np.empty((nray, 3, nsurf + 1))
    # First point on each ray is where it enters the start surface.
    transform = batoid.CoordTransform(traceFull[start]['inCoordSys'], globalSys)
    xyz[:, :, 0] = np.stack(transform.applyForward(*traceFull[start]['in'].r.T), axis=1)
    # Keep track of the number of visible points on each ray.
    raylen = np.ones(nray, dtype=int)
    for i, surface in enumerate(traceFull[start:end]):
        # Add a point for where each ray leaves this surface.
        transform = batoid.CoordTransform(surface['outCoordSys'], globalSys)
        xyz[:, :, i + 1] = np.stack(transform.applyForward(*surface['out'].r.T), axis=1)
        # Keep track of rays which are still visible.
        visible = ~surface['out'].vignetted
        raylen[visible] += 1
    return xyz, raylen


def drawTrace3d(ax, traceFull, start=None, end=None, **kwargs):
    """Draw 3D rays in global coordinates on the specified axis.
    """
    xyz, raylen = getGlobalRays(traceFull, start, end)
    lines = []
    for line, nline in zip(xyz, raylen):
        ax.plot(line[0, :nline], line[1, :nline], line[2, :nline], **kwargs)


def drawTrace2d(ax, traceFull, start=None, end=None, **kwargs):
    """Draw 2D rays in global coordinates on the specified axis.
    """
    xyz, raylen = getGlobalRays(traceFull, start, end)
    lines = []
    for line, nline in zip(xyz, raylen):
        lines.extend([line[0, :nline], line[2, :nline]])
    ax.plot(*lines, **kwargs)
