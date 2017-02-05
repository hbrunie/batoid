#ifndef __jem_jtrace__h
#define __jem_jtrace__h

#include "vec3.h"
#include "ray.h"
#include "intersection.h"
#include "surface.h"
#include "utils.h"

namespace jtrace {

    class NoIntersectionError
    {
    public:
        explicit NoIntersectionError(const char *_message) : message(_message) {}
        const char *GetMessage() const {return message;}
    private:
        const char * const message;
    };

    class NoFutureIntersectionError
    {
    public:
        explicit NoFutureIntersectionError(const char *_message) : message(_message) {}
        const char *GetMessage() const {return message;}
    private:
        const char * const message;
    };

}

#endif