#ifndef jtrace_paraboloid_h
#define jtrace_paraboloid_h

#include "jtrace.h"

namespace jtrace {

    class Paraboloid : public Surface {
    public:
        Paraboloid(double _A, double _B);
        virtual double operator()(double, double) const;
        virtual Vec3 normal(double, double) const;
        using Surface::intersect;
        virtual Intersection intersect(const Ray&) const;
        double getA() const {return A;}
        double getB() const {return B;}

        std::string repr() const;

    private:
        const double A, B;
    };

    inline std::ostream& operator<<(std::ostream& os, const Paraboloid& p);

}
#endif
