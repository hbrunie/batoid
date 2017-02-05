#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "asphere.h"

namespace py = pybind11;

namespace jtrace {
    void pyExportAsphere(py::module &m) {
        py::class_<Asphere, Surface>(m, "Asphere")
            .def(py::init<double,double,std::vector<double>,double>())
            .def_property_readonly("R", &Asphere::getR)
            .def_property_readonly("kappa", &Asphere::getKappa)
            .def_property_readonly("alpha", &Asphere::getAlpha)
            .def_property_readonly("B", &Asphere::getB)
            .def("__call__", &Asphere::operator())
            .def("normal", &Asphere::normal)
            .def("intersect", &Asphere::intersect)
            .def("__repr__", &Asphere::repr);
    }
}