def build_load(flights):

    if len(flights) == 0:
        return [], None
    
    day = min(f.orig_start for f in flights).date()
    load = [0] * 288

    for f in flights:
        if f.status in( "DELAYED" , "CANCELLED") and f.orig_start.date() == day:
            i = (f.orig_start.hour * 60 + f.orig_start.minute) // 5
            load[i] += 1

    return load, day